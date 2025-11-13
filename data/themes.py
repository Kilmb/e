import sqlalchemy

from .db_session import SqlAlchemyBase


class Themes(SqlAlchemyBase):
    __tablename__ = 'themes'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    category_id = sqlalchemy.Column('category', sqlalchemy.Integer, sqlalchemy.ForeignKey('category.id'))
