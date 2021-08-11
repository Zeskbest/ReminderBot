"""
Module with Menus (UI analog).
"""
from __future__ import annotations

import re
from datetime import datetime
from operator import attrgetter
from typing import Optional

from dateutil.relativedelta import relativedelta
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Message, Update, ReplyMarkup
from telegram.ext import Updater, CallbackQueryHandler, CommandHandler, MessageHandler, Filters, CallbackContext

from src.callendar_telegram import telegramcalendar
from src.db import models
from src.processors.reminder_processor import Reminder, ReminderField, NothingToDo


class ReminderNotFound(Exception):
    """Exception is raised if remonder lost."""


class _Menu:
    """Base Menu class."""

    name: str  # Menu name
    link: str  # Menu link
    markup: InlineKeyboardMarkup  # Menu date_markup

    @classmethod
    def apply(cls, updater: Updater) -> None:
        """
        Apply menu handler.

        Args:
            updater: telegram bot updater object
        """
        updater.dispatcher.add_handler(CallbackQueryHandler(cls.handle, pattern=cls.link))

    @classmethod
    def handle(cls, update: Update, context: CallbackContext) -> Message:
        """
        Handle method. Called if the menu link was called.

        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            reply message
        """
        return update.callback_query.message.edit_text(text=cls.name, reply_markup=cls.markup)

    @classmethod
    def resolve_markup(cls, update: Update, context, text: str, reply_markup: Optional[ReplyMarkup] = None) -> Message:
        """
        Remove reply markup (current message buttons) and send raw message with the specified text.

        Args:
            update: telegram update object
            context: telegram context object
            text: text to send
            reply_markup: reply buttons for the new message

        Returns:
            new message
        """
        update.callback_query.message.edit_reply_markup(reply_markup=None)
        # todo use ReplyMarkup

        return context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup,
        )

    @classmethod
    def get_reminder(cls, update: Update, context: CallbackContext, raiseExc: bool = True) -> Optional[Reminder]:
        """
        Get current fulfilling reminder.

        Args:
            update: telegram update object
            context: telegram context object
            raiseExc: whether to raise exception if the reminder was not found

        Returns:
            current fulfilling reminder

        Raises:
            ReminderNotFound if a reminder was not found
        """
        reminder = Reminder.get_current(update)
        if reminder is None:
            if raiseExc:
                cls.resolve_markup(update, context, f"Reminder lost. Create new reminder here: /menu")
                raise ReminderNotFound
            return None
        return reminder


class CancelMenu(_Menu):
    """
    Cancel Menu. Stops reminder creation.
    """

    link = "cancel_reminder"

    @classmethod
    def handle(cls, update: Update, context: CallbackContext) -> Message:
        """
        Stop the reminder creation.

        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            Message with a cat
        """
        Reminder.pop_current(update)
        return cls.resolve_markup(update, context, "ฅ^•ﻌ•^ฅ")


class ReminderNameMenu(_Menu):
    """
    Menu for adding a reminder name.
    """

    link = "add_reminder_name"

    @classmethod
    def handle(cls, update: Update, context: CallbackContext) -> Message:
        """
        Ask user to enter the name.

        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            sent message
        """
        cls.get_reminder(update, context).waiting_for = ReminderField.name
        return cls.resolve_markup(update, context, "Enter Name:")


class ReminderDateMenu(_Menu):
    """
    Menu for adding a first reminder date.
    """

    name = f"Add a reminder create_time:\nToday is{datetime.now().strftime('%e %b %Y')}."
    link = "add_reminder_date"
    markup = telegramcalendar.create_calendar()

    @classmethod
    def apply(cls, updater: Updater) -> None:
        """
        Apply handler for choosing reminder date and processing the calendar buttons.

        Args:
            updater: telegram bot updater object
        """
        super().apply(updater)
        cmd = r"(IGNORE|DAY|PREV-MONTH|NEXT-MONTH)"
        year = r"\d{4}"
        month = r"\d{1,2}"
        day = r"\d{1,2}"
        pattern = rf"{cmd};{year};{month};{day}"
        updater.dispatcher.add_handler(CallbackQueryHandler(cls.handle, pattern=pattern))

    @classmethod
    def handle(cls, update: Update, context: CallbackContext) -> Message:
        """
        Handle the user input.
        Create calendar, change pages or process the selected reminder date.

        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            sent message
        """
        reminder = cls.get_reminder(update, context)
        if update.callback_query.data == cls.link:
            # first appearance
            reminder.waiting_for = ReminderField.date
            return super().handle(update=update, context=context)
        selected, date = telegramcalendar.process_calendar_selection(update=update, context=context)
        if selected:
            if reminder.date is not None:
                hour, minute, second = attrgetter("hour", "minute", "second")(reminder.date)
                date = date.replace(hour=hour, minute=minute, second=second)
            reminder.date = date
            reminder.waiting_for = None
            return AddReminderMenu.handle(update, context)


class ReminderTimeMenu(_Menu):
    """
    Reminder time menu.
    """

    link = "add_reminder_time"

    @classmethod
    def handle(cls, update: Update, context: CallbackContext) -> Message:
        """
        Ask user to specify the reminder time.

        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            sent message
        """
        cls.get_reminder(update, context).waiting_for = ReminderField.time
        return cls.resolve_markup(update, context, Reminder.time_markup_help)


class PeriodMenu(_Menu):
    """
    Reminder period menu.
    """

    link = "add_period"

    @classmethod
    def handle(cls, update: Update, context: CallbackContext) -> Message:
        """
        Ask user to specify the reminder period.

        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            sent message
        """
        cls.get_reminder(update, context).waiting_for = ReminderField.period
        return cls.resolve_markup(update, context, Reminder.date_markup_help)


class SaveMenu(_Menu):
    """
    Save reminder menu.
    """

    link = "save_reminder"

    @classmethod
    def handle(cls, update: Update, context: CallbackContext) -> Message:
        """
        Check the required fields and save tha cached reminder.

        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            sent message
        """
        reminder = cls.get_reminder(update, context)
        for attrName in ("name", "date"):
            if getattr(reminder, attrName) is None:
                cls.resolve_markup(update, context, f"Fulfill the '{attrName}', it is required.")
                return AddReminderMenu.handle_menu(update, context)

        models.Reminder.create(reminder, update)
        Reminder.pop_current(update)
        return cls.resolve_markup(update, context, "Saved successfully.")


class AddReminderMenu(_Menu):
    """
    Add reminder menu.
    """

    name = "Add a reminder:"
    link = "add_reminder"
    markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Choose name", callback_data=ReminderNameMenu.link)],
            [InlineKeyboardButton("Choose first remind date", callback_data=ReminderDateMenu.link)],
            [InlineKeyboardButton("Choose first remind time", callback_data=ReminderTimeMenu.link)],
            [InlineKeyboardButton("Choose period", callback_data=PeriodMenu.link)],
            [InlineKeyboardButton("Save", callback_data=SaveMenu.link)],
            [InlineKeyboardButton("Cancel", callback_data=CancelMenu.link)],
        ]
    )

    @classmethod
    def handle(cls, update: Update, context: CallbackContext) -> Message:
        """
        Handle the incoming message,

        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            sent message
        """
        reminder = Reminder.get_current(update)
        if reminder is not None:
            if reminder.waiting_for is not None:
                reminder.waiting_for = None
        else:
            reminder = Reminder(update)
        text = f"{cls.name}\n" f"{reminder}"
        if update.callback_query is None:
            # when came from the outside
            return update.message.reply_text(text=text, reply_markup=cls.markup)
        return update.callback_query.message.edit_text(text=text, reply_markup=cls.markup)

    @classmethod
    def handle_menu(cls, update: Update, context: CallbackContext) -> Message:
        """
        Handler menu appearance.

        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            sent message
        """
        reminder = Reminder.get_current(update)
        if reminder is not None:
            if reminder.waiting_for is not None:
                reminder.waiting_for = None
        else:
            reminder = Reminder(update)
        text = f"{cls.name}\n" f"{reminder}"  # todo rm copypaste
        return update.effective_chat.send_message(text=text, reply_markup=cls.markup)


class MainMenu(_Menu):
    """
    Main menu.
    """

    name = "Main menu:"
    link = "main_menu"
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Add reminder", callback_data=AddReminderMenu.link),
                InlineKeyboardButton("Close", callback_data=CancelMenu.link),
            ],
            # [InlineKeyboardButton("Reminder list", callback_data="_")],
            # [InlineKeyboardButton("Remove reminder", callback_data="_")],
        ]
    )

    @classmethod
    def handle_start(cls, update: Update, context: CallbackContext) -> Message:
        """
        Handle /start command.
        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            sent message
        """
        models.User.get_or_create(update)
        return update.message.reply_text(text=cls.name, reply_markup=cls.markup)

    @classmethod
    def handle_menu(cls, update: Update, context: CallbackContext) -> Message:
        """
        Handle /menu command.
        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            sent message
        """
        return update.effective_chat.send_message(text=cls.name, reply_markup=cls.markup)

    @classmethod
    def apply(cls, updater: Updater) -> None:
        """
        Apply handler and command handlers.

        Args:
            updater: telegram updater object
        """
        updater.dispatcher.add_handler(CommandHandler("start", cls.handle_start))
        updater.dispatcher.add_handler(CommandHandler("menu", cls.handle_menu))
        super().apply(updater)


class ReminderMsg(_Menu):
    """
    Reminder message menu.
    """

    # generate link for the reminder
    gen_link = lambda reminder_id, action: f"reminder_{reminder_id}_action_{action}"
    link = gen_link(r"(\d+)", r"(SNOOZE15|SNOOZE60|DONE|SKIP|REMOVE|NOT_SELECTED)")

    @classmethod
    def handle_first(cls, context: CallbackContext, reminder: models.Reminder) -> Message:
        """
        Handle appearance.

        Args:
            context: telegram context object
            reminder: db reminder object

        Returns:
            sent message
        """
        reminder_id = reminder.id
        text = f"Reminder: {reminder_id}\n" f"{reminder.text}"
        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("15min later", callback_data=cls.gen_link(reminder_id, "SNOOZE15")),
                    InlineKeyboardButton("1h later", callback_data=cls.gen_link(reminder_id, "SNOOZE60")),
                ],
                [
                    InlineKeyboardButton("Done", callback_data=cls.gen_link(reminder_id, "DONE")),
                    InlineKeyboardButton("Skip", callback_data=cls.gen_link(reminder_id, "SKIP")),
                    InlineKeyboardButton("!Remove!", callback_data=cls.gen_link(reminder_id, "REMOVE")),  # todo emoji
                ],
            ]
        )
        chat_id = models.Reminder.get(reminder_id).chat_id
        return context.bot.send_message(text=text, chat_id=chat_id, reply_markup=markup)

    @classmethod
    def handle(cls, update: Update, context: CallbackContext) -> Message:
        """
        Handle tap on the reminder.
        Make an action according to the inpout data.

        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            sent message
        """
        reminder_id, action = re.match(cls.link, update.callback_query.data).groups()
        reminder_id = int(reminder_id)
        reminder = models.Reminder.get(reminder_id)
        text = ""
        if action == "DONE":
            reminder.success()
            text = "Reminder marked as Done."
        elif action == "SKIP":
            reminder.skip()
            text = "Reminder marked as Skip."
        elif action == "REMOVE":
            reminder.stop()
        elif action in ("SNOOZE15", "SNOOZE60"):
            snooze = int(action[len("SNOOZE") :])
            reminder.snooze(relativedelta(minutes=snooze))
            text = "Reminder marked as Snooze."
        else:
            raise NotImplementedError(f"Unknown action: {action}")

        reminder = models.Reminder.get(reminder_id)
        if reminder.status == 1:
            text += "\nReminder is active, next remind in " + reminder.remind_time_real.strftime("%d.%m.%Y %H:%M:%S")
        else:
            text += "\nReminder ended."
        return cls.resolve_markup(update, context, text)


class RawMessagesProcessor(_Menu):
    """
    Raw message menu.
    """

    @classmethod
    def handle(cls, update: Update, context: CallbackContext) -> Message:
        """
        Handle raw input from user.
        Try to update a pending reminder.
        If succeeded, respond with `AddReminderMenu`.
        Otherwise, ask user to do allowed things.

        Args:
            update: telegram update object
            context: telegram context object

        Returns:
            reply message
        """
        try:
            cls.get_reminder(update, context).process(update)
        except (NothingToDo, ReminderNotFound, ValueError):
            return update.message.reply_text(text=f"Unsupported command '{update.message.text}' try again.")
        return AddReminderMenu.handle(update, context)

    @classmethod
    def apply(cls, updater: Updater) -> None:
        """
        Apply the handler to the all text messages.

        Args:
            updater: telegram updater object
        """
        updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, cls.handle, pass_chat_data=True))


def apply_menus(updater: Updater) -> None:
    """
    Apply all the menus, that are inherited from the  _Menu class.

    Args:
        updater: telegram updater object
    """
    menus = _Menu.__subclasses__()
    for menu in menus:
        menu.apply(updater)
