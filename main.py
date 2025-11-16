from flask import Flask, render_template, redirect, request, abort, Response, send_from_directory, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy.orm import joinedload
from forms.news import NewsForm
from forms.user import RegisterForm, LoginForm
from data.news import News
from data.users import User
from data import db_session
from data.category import Category
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


def main():
    db_session.global_init("db/blogs.db")
    app.run()


@app.route('/news', methods=['GET', 'POST'])
@login_required
def add_news():
    form = NewsForm()
    db_sess = db_session.create_session()
    existing_categories = db_sess.query(Category).all()
    category_names = [c.name for c in existing_categories]

    if form.validate_on_submit():
        news = News()
        news.title = form.title.data
        news.content = form.content.data
        news.is_private = form.is_private.data
        news.user_id = current_user.id
        news.due_date = form.due_date.data
        if form.file.data:
            file = form.file.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                news.file_name = filename
        if form.category_name.data:
            category_name = form.category_name.data.strip()
            category = db_sess.query(Category).filter(Category.name == category_name).first()
            if not category:
                category = Category(name=category_name)
                db_sess.add(category)
                db_sess.commit()
            news.category_id = category.id

        db_sess.add(news)
        db_sess.commit()
        db_sess.close()
        return redirect('/')

    db_sess.close()
    return render_template('news.html', title='Добавление новости', form=form, existing_categories=category_names)


@app.route('/file/<int:news_id>')
@login_required
def get_file(news_id):
    db_sess = db_session.create_session()
    news = db_sess.query(News).filter(News.id == news_id, News.user_id == current_user.id).first()

    if news and news.file_name:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], news.file_name)

        if os.path.exists(filepath):
            if news.file_name.lower().endswith(('.jpg', '.jpeg')):
                mimetype = 'image/jpeg'
            elif news.file_name.lower().endswith('.png'):
                mimetype = 'image/png'
            elif news.file_name.lower().endswith('.gif'):
                mimetype = 'image/gif'
            elif news.file_name.lower().endswith('.pdf'):
                mimetype = 'application/pdf'
            elif news.file_name.lower().endswith('.txt'):
                mimetype = 'text/plain'
            elif news.file_name.lower().endswith('.doc'):
                mimetype = 'application/msword'
            elif news.file_name.lower().endswith('.docx'):
                mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif news.file_name.lower().endswith('.zip'):
                mimetype = 'application/zip'
            else:
                mimetype = 'application/octet-stream'

            return send_file(filepath, mimetype=mimetype)

    abort(404)


@app.route('/news_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def news_delete(id):
    db_sess = db_session.create_session()
    news = db_sess.query(News).filter(News.id == id, News.user_id == current_user.id).first()
    if news:
        if news.file_name:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], news.file_name)
            if os.path.exists(filepath):
                os.remove(filepath)

        db_sess.delete(news)
        db_sess.commit()
    else:
        abort(404)
    db_sess.close()
    return redirect('/')


@app.route('/news_ready/<int:id>', methods=['GET'])
@login_required
def news_ready(id):
    db_sess = db_session.create_session()
    news_item = db_sess.query(News).filter(News.id == id, News.user_id == current_user.id).first()
    if news_item:
        news_item.is_ready = True
        db_sess.commit()
    else:
        abort(404)

    db_sess.close()
    return redirect('ready')


@app.route('/ready', methods=['GET'])
@login_required
def ready():
    db_sess = db_session.create_session()

    selected_category = request.args.get('category', 'all')
    categories = db_sess.query(Category).all()
    query = db_sess.query(News).options(joinedload(News.category)).filter(News.user_id == current_user.id,
                                                                          News.is_ready == True)
    if selected_category == 'no_category':
        query = query.filter(News.category_id == None)
    elif selected_category != 'all':
        category = db_sess.query(Category).filter(Category.name == selected_category).first()
        if category:
            query = query.filter(News.category_id == category.id)
        else:
            query = query.filter(News.id == -1)
    news = query.all()
    db_sess.close()

    return render_template('ready.html', news=news, categories=categories,
                           selected_category=selected_category)


@app.route('/news_not_ready/<int:id>', methods=['GET'])
@login_required
def news_not_ready(id):
    db_sess = db_session.create_session()

    news_item = db_sess.query(News).filter(News.id == id, News.user_id == current_user.id).first()
    if news_item:
        news_item.is_ready = False
        db_sess.commit()
    else:
        abort(404)

    db_sess.close()
    return redirect('/')


@app.route('/news/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_news(id):
    form = NewsForm()
    db_sess = db_session.create_session()

    if request.method == "GET":
        news = db_sess.query(News).options(joinedload(News.category)).filter(News.id == id,
                                                                             News.user_id == current_user.id).first()
        if news:
            form.title.data = news.title
            form.content.data = news.content
            form.is_private.data = news.is_private
            form.due_date.data = news.due_date
            if news.category:
                form.category_name.data = news.category.name
        else:
            db_sess.close()
            abort(404)

    if form.validate_on_submit():
        news = db_sess.query(News).filter(News.id == id, News.user_id == current_user.id).first()
        if news:
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            news.due_date = form.due_date.data
            if form.file.data:
                file = form.file.data
                if file and allowed_file(file.filename):
                    if news.file_name:
                        old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], news.file_name)
                        if os.path.exists(old_filepath):
                            os.remove(old_filepath)
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    news.file_name = filename

            if form.category_name.data:
                category = db_sess.query(Category).filter(Category.name == form.category_name.data).first()
                if not category:
                    category = Category(name=form.category_name.data)
                    db_sess.add(category)
                    db_sess.commit()
                news.category_id = category.id
            else:
                news.category_id = None

            db_sess.commit()
            db_sess.close()
            return redirect('/')
        else:
            db_sess.close()
            abort(404)

    db_sess.close()
    return render_template('news.html', title='Редактирование новости', form=form, existing_categories=[])


@app.route("/")
def index():
    db_sess = db_session.create_session()

    categories = db_sess.query(Category).all()
    selected_category = request.args.get('category', 'all')

    if current_user.is_authenticated:
        query = db_sess.query(News).options(joinedload(News.category)).filter(News.user_id == current_user.id,
            News.is_ready != True)

        if selected_category == 'no_category':
            query = query.filter(News.category_id == None)
        elif selected_category != 'all':
            category = db_sess.query(Category).filter(Category.name == selected_category).first()
            if category:
                query = query.filter(News.category_id == category.id)
            else:
                query = query.filter(News.id == -1)

        news = query.all()
    else:
        news = db_sess.query(News).options(joinedload(News.category)).filter(News.is_private == True).all()

    db_sess.close()

    return render_template("index.html", news=news, categories=categories,
                           selected_category=selected_category)


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        db_sess.close()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        db_sess.close()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', message="Неправильный логин или пароль", form=form)
    return render_template('login.html', title='Авторизация', form=form)


if __name__ == '__main__':
    main()