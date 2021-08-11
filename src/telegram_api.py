import os
import traceback

from dateutil.relativedelta import relativedelta
from telegram import Update
from telegram.ext import Updater, CallbackContext

from src.db import models
from src.menus import apply_menus, ReminderMsg


def error(update: Update, context: CallbackContext) -> None:
    """
    Error handler.

    Args:
        update: telegram update object
        context: telegram context object
    """
    print(f"Update\n{update}\nerror")
    try:
        raise context.error
    except Exception:
        traceback.print_exc()


def push_reminders(context: CallbackContext):
    """
    Push actual reminders.

    Args:
        context: telegram context object
    """
    for reminder in models.Reminder.get_actual_reminders():
        ReminderMsg.handle_first(context, reminder)
        reminder.snooze(relativedelta(days=1))


def main() -> None:
    """
    Entrypoint for the bot.
    Handlers and repeating callbacks registration.
    """
    try:
        ############################# Handlers #########################################
        updater = Updater(os.environ["TELEGRAM_TOKEN"], use_context=True)
        apply_menus(updater)
        updater.dispatcher.add_error_handler(error)
        ############################# Repeating ########################################
        updater.job_queue.run_repeating(push_reminders, 10)
        updater.start_polling(timeout=0.1)
        updater.idle()
    finally:
        print("The bot stopped")
