"""
Database models here.
"""
import sqlalchemy as sa

from src.db import Base


class User(Base):
    __tablename__ = "user"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    chat_id = sa.Column(sa.Integer, nullable=False)
    telegram_id = sa.Column(sa.Integer, nullable=False, unique=True, index=True)
    telegram_name = sa.Column(sa.String, nullable=False)
    first_name = sa.Column(sa.String)
    last_name = sa.Column(sa.String)
    karma = sa.Column(sa.Integer)

    def good(self) -> bool:
        """
        Whether to response to him.

        Returns:
            bool
        """
        return self.karma > 0


class UserGroup(Base):
    __tablename__ = "user_group"

    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), primary_key=True)
    group_id = sa.Column(sa.Integer, sa.ForeignKey("group.id"), primary_key=True)


class Group(Base):
    __tablename__ = "group"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)


class Reminder(Base):
    __tablename__ = "reminder"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    text = sa.Column(sa.String)
    date = sa.Column(sa.DateTime)
    period = sa.Column(sa.Interval, nullable=True)
    status = sa.Column(sa.SmallInteger)
    group_id = sa.Column(sa.Integer, sa.ForeignKey("group.id"))


# class Admin(Base):
#     __tablename__ = 'admin'
#
#     id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), primary_key=True)


class PendingTask(Base):
    __tablename__ = "pending_task"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
