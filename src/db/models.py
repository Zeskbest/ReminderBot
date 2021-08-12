"""
Database models here.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

import sqlalchemy as sa
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from telegram import Update

from src.db import Base, engine, metadata
from src.processors.reminder_processor import Reminder as ReminderObj


class User(Base):
    """User model"""

    __tablename__ = "user"

    telegram_id = sa.Column(sa.Integer, primary_key=True)
    telegram_name = sa.Column(sa.String, nullable=False)
    first_name = sa.Column(sa.String)
    last_name = sa.Column(sa.String)

    def good(self) -> bool:
        """
        Whether to respond him.

        Returns:
            bool
        """
        return self.karma > 0

    @classmethod
    def get_or_create(cls, update: Update) -> ChatUser:
        """
        Get or create a user.

        Args:
            update: telegram update object

        Returns:
            found or created user
        """
        with Session(engine) as sess:
            user = sess.query(cls).filter_by(telegram_id=update.effective_user.id).one_or_none()
            if user is None:
                user = cls(
                    telegram_id=update.effective_user.id,
                    telegram_name=update.effective_user.name,
                    first_name=update.effective_user.first_name,
                    last_name=update.effective_user.last_name,
                )
                sess.add(user)
                sess.commit()
            return user


class Chat(Base):
    """Chat model"""

    __tablename__ = "chat"

    telegram_id = sa.Column(sa.Integer, primary_key=True)

    @classmethod
    def get_or_create(cls, update: Update) -> Chat:
        """
        Get or create new Chat object.

        Args:
            update: telegram update object

        Returns:
            Chat object
        """
        with Session(engine) as sess:
            attrs = dict(telegram_id=update.effective_chat.id)
            chat = sess.query(Chat).filter_by(**attrs).one_or_none()
            if chat is None:
                chat = Chat(**attrs)
                sess.add(chat)
                sess.commit()
            return chat


class ChatUser(Base):
    """Chat-User model. Main authentication entity."""

    __tablename__ = "chat_user"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.telegram_id"))
    chat_id = sa.Column(sa.Integer, sa.ForeignKey("chat.telegram_id"))
    karma = sa.Column(sa.Float, default=1)

    @classmethod
    def get_or_create(cls, update: Update) -> ChatUser:
        """
        Get or create new chat-user object.

        Args:
            update: telegram update object

        Returns:
            chat-user object
        """
        with Session(engine) as sess:
            user = User.get_or_create(update)
            chat = Chat.get_or_create(update)
            sess.add_all((user, chat))
            attrs = dict(user_id=user.telegram_id, chat_id=chat.telegram_id)
            chatUser = sess.query(ChatUser).filter_by(**attrs).one_or_none()
            if chatUser is None:
                chatUser = ChatUser(**attrs)
                sess.add(chatUser)
                sess.commit()
            return chatUser


class Reminder(Base):
    """Reminder model."""

    __tablename__ = "reminder"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    text = sa.Column(sa.String)
    create_time = sa.Column(sa.DateTime)
    remind_time_planned = sa.Column(sa.DateTime)
    remind_time_real = sa.Column(sa.DateTime)
    period = sa.Column(sa.String, nullable=True)
    status = sa.Column(sa.SmallInteger)
    chat_user = sa.Column(sa.Integer, sa.ForeignKey("chat_user.id"))

    @classmethod
    def get(cls, reminder_id: int) -> Reminder:
        """
        Get reminder by id.

        Args:
            reminder_id: reminder id

        Returns:
            reminder object
        """
        with Session(engine) as sess:
            return sess.get(Reminder, reminder_id)

    @classmethod
    def create(cls, reminder_obj: ReminderObj, update: Update) -> Reminder:
        """
        Create new reminder.

        Args:
            reminder_obj: fulfilled ReminderObj
            update: telegram update object

        Returns:
            created reminder
        """
        with Session(engine) as sess:
            chat_user = ChatUser.get_or_create(update)
            reminder = cls(
                text=reminder_obj.name,
                create_time=reminder_obj.date,
                remind_time_planned=reminder_obj.date,
                remind_time_real=reminder_obj.date,
                period=str(reminder_obj.period),
                status=1,
                chat_user=chat_user.id,
            )
            sess.add(reminder)
            sess.commit()
            return reminder

    @classmethod
    def get_actual_reminders(cls) -> List[Reminder]:
        """
        Get actual reminders.

        Returns:
            reminders
        """
        with Session(engine) as sess:
            reminderAndChatPairs = (
                sess.query(Reminder).filter(Reminder.status == 1, Reminder.remind_time_real <= datetime.now()).all()
            )
        return reminderAndChatPairs

    @property
    def chat_id(self) -> int:
        """
        Chat id property.

        Returns:
            telegram chat id
        """
        with Session(engine) as sess:
            chat_id = sess.query(Chat.telegram_id).join(ChatUser).join(Reminder).filter(Reminder.id == self.id).scalar()
            return chat_id

    def get_chat_user(self) -> ChatUser:
        """
        Chat-user property.

        Returns:
            chat-user
        """
        with Session(engine) as sess:
            sess.add(self)
            chat_user = sess.query(ChatUser).join(Reminder).filter(Reminder.id == self.id).scalar()
            return chat_user

    def rewind(self) -> None:
        """
        Rewind to the next reminder time.
        Or end it if the reminder period is empty.
        """
        locals_ = {}
        exec(f"delta = {self.period}", {"relativedelta": relativedelta}, locals_)
        delta = locals_["delta"]
        if delta is None:
            self.stop()
        else:
            with Session(engine) as sess:
                while self.remind_time_planned < datetime.now():
                    self.remind_time_real = self.remind_time_planned = self.remind_time_planned + delta
                sess.add(self)
                sess.commit()

    def success(self) -> None:
        """
        Reminder was successful.
        """
        self.rewind()

        chat_user = self.get_chat_user()
        # todo separate func
        with Session(engine) as sess:
            chat_user.karma += 1
            sess.add(chat_user)
            sess.commit()

    def snooze(self, delta: relativedelta) -> None:
        """
        Set reminder time some time forward.

        Args:
            delta: delta to add
        """
        with Session(engine) as sess:
            self.remind_time_real = datetime.now() + delta
            sess.add(self)
            sess.commit()

        chat_user = self.get_chat_user()
        # todo separate func
        with Session(engine) as sess:
            chat_user.karma -= 0.1
            sess.add(chat_user)
            sess.commit()

    def skip(self) -> None:
        """
        Skip this reminder one time.
        """
        self.rewind()

    def stop(self) -> None:
        """
        Stop the reminder.
        """
        with Session(engine) as sess:
            self.status = 0
            sess.add(self)
            sess.commit()


metadata.create_all()
