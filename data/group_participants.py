import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm


class GroupParticipants(SqlAlchemyBase):
    __tablename__ = 'group_participants'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                                primary_key=True, autoincrement=True)
    group_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    # + ссылка на ученика
