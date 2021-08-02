from __future__ import annotations
import re
from datetime import timedelta, datetime
from enum import Enum, auto
from typing import Tuple, Mapping, Optional, Union, MutableMapping

from cachetools import TTLCache
from dateutil.relativedelta import relativedelta
from telegram import Update


class AlreadyInProcess(Exception):
    """Raised if a user requests to get_or_create the second reminder (allowed only one at one time)."""


class NothingToDo(Exception):
    """Raised if a user requests unknown reminder update."""


class ReminderField(Enum):
    name = auto()
    date = auto()
    time = auto()
    period = auto()


class Reminder:
    cache: MutableMapping[int, Reminder] = TTLCache(100000, 3600)

    markup = {
        "y": relativedelta(years=1),
        "mon": relativedelta(months=1),
        "w": relativedelta(days=7),
        "d": relativedelta(days=1),
        "h": relativedelta(hours=1),
        "min": relativedelta(minutes=1),
    }
    date_markup_help = (
        "Specify time period in the following format: \n"
        "'<amount><symbol>', where symbol is one of the following:"
        "'min' for minutes\n"
        "'h'   for hours\n"
        "'d'   for days\n"
        "'w'   for weeks\n"
        "'mon' for months\n"
        "'y'   for years\n"
        "Example: 1h30min\n"
    )
    time_markup_help = (
        "Specify time in the following format: \n"
        "'hour:minute:second', minute and second are not required.\n"
        "Example: 9:30\n"
    )

    def __init__(self, update: Update):
        if self.get_current(update):
            raise AlreadyInProcess

        self.waiting_for: Optional[ReminderField] = None
        self.name: Optional[str] = None
        self.date: Optional[datetime] = None
        self.period: Optional[relativedelta] = None

        self.cache[self.get_cache_id(update)] = self

    @classmethod
    def parsePeriod(cls, period: str) -> relativedelta:
        # todo more strict
        oneRe = r"(\d+[^\d]+)"
        manyRe = rf"{oneRe}+"
        period = period.lower().replace(" ", "")
        if re.match(manyRe, period):
            result = relativedelta()
            for amountAndType in re.findall(oneRe, period):
                amount, partType = re.match(r"(\d+)([^\d]+)", amountAndType).groups()
                amount = int(amount)
                scale = cls.markup[partType]
                result += scale * amount
            return result
        else:
            raise ValueError(f"Cannot process: '{period}'\n{cls.date_markup_help}")

    @classmethod
    def parseTime(cls, time: str) -> list[int]:  # remove typing
        parts = list(map(int, time.replace(" ", "").split(":")))
        parts += [0] * (3 - len(parts))
        return parts

    @staticmethod
    def get_cache_id(update: Update) -> int:
        return update.effective_message.chat_id

    @classmethod
    def get_current(cls, update: Update) -> Optional[Reminder]:
        instance = cls.cache.get(cls.get_cache_id(update))
        return instance

    @classmethod
    def pop_current(cls, update: Update) -> Reminder:
        cache_id = cls.get_cache_id(update)
        return cls.cache.pop(cache_id, None)

    def process(self, update: Update) -> bool:
        if self.waiting_for == ReminderField.name:
            self.name = update.message.text
            self.waiting_for = None
        elif self.waiting_for == ReminderField.period:
            self.period = self.parsePeriod(update.message.text)
            self.waiting_for = None
        elif self.waiting_for == ReminderField.time:
            if self.date is None:
                self.date = datetime.now()
            hour, minute, second = self.parseTime(update.message.text)
            self.date = self.date.replace(hour=hour, minute=minute, second=second)
            self.waiting_for = None
        else:
            raise NothingToDo
        return True

    def __str__(self):
        return (
            "name: " + (f"{self.name}" if self.name else "<unnamed>") + "\n"
            "reminder date: " + (f"{self.date.strftime('%d.%m.%Y %H:%M:%S')}" if self.date else "<no date>") + "\n"
            "period: " + (f"{self.period}" if self.period else "no period")
        )
