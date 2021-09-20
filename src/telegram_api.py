import os
import traceback

from telegram import Update
from telegram.ext import Updater, CallbackContext

from src.db import models
from src.menus import apply_menus
from src.processors.old_messages_remover import MessagesRemover


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
        context.bot.send_message(text=reminder.text, chat_id=models.Reminder.get(reminder.id).chat_id)
        reminder.success()


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
        MessagesRemover.listen_bot(updater.bot)
        ############################# Repeating ########################################
        updater.job_queue.run_repeating(push_reminders, 10)
        updater.job_queue.run_repeating(MessagesRemover.remove_messages, 10)
        updater.start_polling(timeout=0.3)
        updater.idle()
    finally:
        print("The bot stopped")
