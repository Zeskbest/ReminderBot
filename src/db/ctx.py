"""
Database interface.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from src.db import engine, metadata
from src.db.models import User, Group, Reminder, UserGroup


class DBContext:
    def __init__(self):
        metadata.create_all()

    def create_user(
        self,
        chat_id: int,
        telegram_id: int,
        telegram_name: str,
        first_name: str,
        last_name: str,
    ) -> int:
        new_user = User(
            chat_id=chat_id,
            telegram_id=telegram_id,
            telegram_name=telegram_name,
            first_name=first_name,
            last_name=last_name,
            karma=1,
        )
        his_group = Group()
        with Session(engine) as session:
            existent = session.query(User).filter(User.telegram_id == telegram_id).one_or_none()
            if existent is not None:
                return existent.id

            session.add_all((new_user, his_group))
            session.flush()
            link = UserGroup(
                user_id=new_user.id,
                group_id=his_group.id,
            )
            session.add(link)
            session.commit()
            return new_user.id

    def add_reminder(self, telegram_id: int, text: str, date: datetime, period: Optional[timedelta]):
        with Session(engine) as session:
            group = (
                session.query(Group)
                .filter(
                    User.telegram_id == telegram_id,
                    UserGroup.user_id == User.id,
                    Group.id == UserGroup.group_id,
                )
                .one()
            )

            reminder = Reminder(
                text=text,
                date=date,
                period=period,
                status=1,
                group_id=group.id,
            )
            session.add(reminder)
            session.commit()
            return reminder.id

    def get_actual_reminder_users_pair(self) -> Tuple[Reminder, List[User]]:
        with Session(engine) as session:
            reminders = session.query(Reminder).filter(Reminder.status == 1, Reminder.date <= datetime.now()).all()
            if not reminders:
                return (None, [])
            reminder = reminders[0]
            users = (
                session.query(User)
                .filter(
                    Reminder.group_id == UserGroup.group_id,
                    User.id == UserGroup.user_id,
                )
                .all()
            )
        return reminder, users

    def succeeded_reminder(self, reminder_id: int):
        with Session(engine) as session:
            reminder = session.get(Reminder, reminder_id)
            if reminder.period is None:
                reminder.status = 0
            else:
                reminder.date += reminder.period
            session.commit()

    def failed_reminder(self, reminder_id: int):
        with Session(engine) as session:
            reminder = session.get(Reminder, reminder_id)
            reminder.date += timedelta(hours=1)
            session.commit()
