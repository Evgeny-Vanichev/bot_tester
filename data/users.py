import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Users(SqlAlchemyBase, UserMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    surname = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    contact_type = sqlalchemy.Column(sqlalchemy.String, nullable=True)  # Discord/Telegram/VK
    contact_link = sqlalchemy.Column(sqlalchemy.String, nullable=True)  # Ссылка
    type = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    tests = orm.relation("Tests", back_populates='teacher')

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def __repr__(self):
        s = str(self)
        if self.type == 1:
            return f'<Teacher> {s}'
        return f'<Student> {s}'

    def __str__(self):
        return f'{self.surname} {self.name}'
