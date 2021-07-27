from abc import abstractmethod, ABCMeta
from typing import Optional

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyMarkup, ForceReply, Message
from telegram.ext import Updater, CallbackQueryHandler, CommandHandler, MessageHandler, Filters

from src.callendar_telegram import telegramcalendar


class Menu(metaclass=ABCMeta):
    @property
    @abstractmethod
    def name(self) -> str:
        """Menu name"""

    @property
    @abstractmethod
    def link(self) -> str:
        """Menu link"""

    @property
    @abstractmethod
    def markup(self) -> InlineKeyboardMarkup:
        """
        Menu content.

        Returns:
            dict with fields:
        """

    def handle(self, update, context):
        update.callback_query.message.edit_text(text=self.name, reply_markup=self.markup)

    def apply(self, updater: Updater):
        updater.dispatcher.add_handler(CallbackQueryHandler(self.handle, pattern=self.link))


class AddReminderNameMenu(Menu):
    name = "Choose reminder name:"
    link = "add_reminder_name"
    markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Cancel", callback_data="_")],
        ]
    )

    def handle(self, update, context):
        super().handle(update, context)


class AddReminderDateMenu(Menu):
    name = "Add a reminder date:"
    link = "add_reminder_date"
    markup = telegramcalendar.create_calendar()

    def apply(self, updater: Updater):
        super().apply(updater)
        cmd = r"(IGNORE|DAY|PREV-MONTH|NEXT-MONTH)"
        year = r"\d{4}"
        month = r"\d{1,2}"
        day = r"\d{1,2}"
        pattern = rf"{cmd};{year};{month};{day}"
        updater.dispatcher.add_handler(CallbackQueryHandler(self.handle, pattern=pattern))

    def handle(self, update, context):
        if update.callback_query.data == self.link:
            # first appearance
            super().handle(update=update, context=context)
        else:
            selected, date = telegramcalendar.process_calendar_selection(update=update, context=context)
            if selected:
                context.bot.send_message(
                    chat_id=update.callback_query.from_user.id,
                    text="You selected %s" % (date.strftime("%d/%m/%Y")),
                    reply_markup=ReplyKeyboardRemove(),
                )


class AddReminderMenu(Menu):
    name = "Add a reminder:"
    link = "add_reminder"
    markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Choose name", callback_data=AddReminderNameMenu.link)],
            [InlineKeyboardButton("Choose date", callback_data=AddReminderDateMenu.link)],
            [InlineKeyboardButton("Choose period", callback_data="_")],
            [InlineKeyboardButton("Save", callback_data="_")],
            [InlineKeyboardButton("Cancel", callback_data="_")],
        ]
    )


class MainMenu(Menu):
    name = "Main menu:"
    link = "main_menu"
    markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Add reminder", callback_data=AddReminderMenu.link)],
            [InlineKeyboardButton("Reminder list", callback_data="_")],
            [InlineKeyboardButton("Remove reminder", callback_data="_")],
        ]
    )

    def handle_start(self, update, context):
        update.message.reply_text(text=self.name, reply_markup=self.markup)

    def apply(self, updater: Updater):
        updater.dispatcher.add_handler(CommandHandler("start", self.handle_start))
        super(MainMenu, self).apply(updater)


class RawMessagesProcessor:
    def handle(self, update, context):
        update.message.reply_text(text=f"Unknown '{update.message.text}'")

    def apply(self, updater: Updater):
        updater.dispatcher.add_handler(
            MessageHandler(Filters.text & ~Filters.command, self.handle, pass_chat_data=True)
        )


# todo apply all the menus automatically
def apply_menus(updater: Updater) -> None:
    menus = [
        AddReminderNameMenu(),
        AddReminderDateMenu(),
        AddReminderMenu(),
        MainMenu(),
        RawMessagesProcessor(),
    ]
    for menu in menus:
        menu.apply(updater)
