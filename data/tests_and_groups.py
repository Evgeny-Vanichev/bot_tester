import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm
from flask_login import UserMixin


class TestsAndGroups(SqlAlchemyBase, UserMixin):
    __tablename__ = 'tasks_and_groups'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    test_id = sqlalchemy.Column(sqlalchemy.Integer,
                                sqlalchemy.ForeignKey("tasks.test_id"))
    group_id = sqlalchemy.Column(sqlalchemy.Integer,
                                 sqlalchemy.ForeignKey("groups.group_id"))
    test = orm.relation('Tests')
    group = orm.relation('Groups')

    def __repr__(self):
        return f'<Test and Group> {self.test_id} {self.group_id}'
