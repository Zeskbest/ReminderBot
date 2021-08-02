import os
import traceback

from dateutil.relativedelta import relativedelta
from telegram import Update
from telegram.ext import Updater, CallbackContext

from src.db import models
from src.menus import apply_menus, ReminderMsg


def error(update: Update, context: CallbackContext) -> None:
    print(f"Update\n{update}\nerror")
    try:
        raise context.error
    except:
        traceback.print_exc()


def push_reminders(context: CallbackContext) -> None:
    for reminder in models.Reminder.get_actual_reminders():
        ReminderMsg.handle_first(context, reminder)
        reminder.snooze(relativedelta(days=1))


def main() -> None:
    ############################# Handlers #########################################
    updater = Updater(os.environ["TELEGRAM_TOKEN"], use_context=True)
    apply_menus(updater)
    updater.dispatcher.add_error_handler(error)
    updater.job_queue.run_repeating(push_reminders, 10)
    updater.start_polling(timeout=0.1)
    ################################################################################
    updater.idle()
    # todo add message stop process
