import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm


class GroupParticipants(SqlAlchemyBase):
    __tablename__ = 'group_participants'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    student_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    student = orm.relation('Users')
    group_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('groups.group_id'))
    group = orm.relation('Groups')
    # + ссылка на ученика

    def __repr__(self):
        return f'<Group Participant> {self.group} {self.student}'

    def __str__(self):
        return f'{self.group} {self.student}'
