import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm


class Groups(SqlAlchemyBase):
    __tablename__ = 'groups'

    group_id = sqlalchemy.Column(sqlalchemy.Integer,
                                 primary_key=True, autoincrement=True)
    group_name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    teacher_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    teacher = orm.relation('Users')
    # + ссылка на учителя

    def __repr__(self):
        return f'<Group> {self.group_name}'

    def __str__(self):
        return str(self.group_name)
