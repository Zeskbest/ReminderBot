#!/usr/bin/env python3.8
import os
from abc import ABC, abstractmethod

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
from telegram.ext import Updater

# TODO REMOVE UNUSED
############################### Bot ############################################
from src.menus import apply_menus


def start_handler(bot, update):
    bot.message.reply_text(**main_menu())


def main_menu_handler(bot, update):
    bot.callback_query.message.edit_text(**main_menu())


def add_reminder_handler(bot, update):
    bot.callback_query.message.edit_text(**add_reminder())


def second_menu_handler(bot, update):
    bot.callback_query.message.edit_text(second_menu_message(), reply_markup=second_menu_keyboard())


def third_menu_handler(bot, update):
    bot.callback_query.message.edit_text(second_menu_message(), reply_markup=second_menu_keyboard())


def first_submenu(bot, update):
    pass


def second_submenu(bot, update):
    pass


def error(update, context):
    print(f"Update {update} caused error {context.error}")


############################ Keyboards #########################################
def main_menu():
    keyboard = [
        [InlineKeyboardButton("Add reminder", callback_data="add_reminder")],
        [InlineKeyboardButton("Reminder list", callback_data="get_reminders")],
        [InlineKeyboardButton("Remove reminder", callback_data="delete_reminder")],
    ]
    return dict(text="Main menu:", reply_markup=InlineKeyboardMarkup(keyboard))


def add_reminder():
    keyboard = [
        [InlineKeyboardButton("", callback_data="m1_1")],
        [InlineKeyboardButton("Submenu 1-2", callback_data="m1_2")],
        [InlineKeyboardButton("Main menu", callback_data="main")],
    ]
    return dict(text="Add a reminder", reply_markup=InlineKeyboardMarkup(keyboard))


def second_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Submenu 2-1", callback_data="m2_1")],
        [InlineKeyboardButton("Submenu 2-2", callback_data="m2_2")],
        [InlineKeyboardButton("Main menu", callback_data="main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def third_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Submenu 2-1", callback_data="m2_1")],
        [InlineKeyboardButton("Submenu 2-2", callback_data="m2_2")],
        [InlineKeyboardButton("Main menu", callback_data="main")],
    ]
    return InlineKeyboardMarkup(keyboard)


############################# Messages #########################################


def second_menu_message():
    return "Choose the submenu in second menu:"


def HE_WROTE_SMHT(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(update.callback_query.data)


def main() -> None:
    ############################# Handlers #########################################
    updater = Updater(os.environ["TELEGRAM_TOKEN"], use_context=True)
    apply_menus(updater)
    updater.dispatcher.add_error_handler(error)

    updater.start_polling(timeout=0.1)
    ################################################################################
    updater.idle()
