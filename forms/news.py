from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional
from wtforms.fields import DateField


class NewsForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired()])
    content = TextAreaField("Содержание")
    is_private = BooleanField("Личное")
    submit = SubmitField('Применить')
    is_ready = BooleanField("Сделано")
    category_name = StringField('Категория (введите название или выберите из существующих)')
    file = FileField('Прикрепить файл')
    due_date = DateField('Срок выполнения', validators=[Optional()])