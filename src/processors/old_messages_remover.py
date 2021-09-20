from telegram import Bot, Message
from telegram.error import BadRequest

from src.db.models import MessageForRemoval


class MessagesRemover:
    """
    Old messages remover.
    """

    @staticmethod
    def remember_msg(msg: Message) -> None:
        """
        Remember a message.

        Args:
            msg: message for removal
        """
        MessageForRemoval.create(msg)

    @classmethod
    def listen_bot(cls, bot: Bot) -> None:
        """
        Monkey-patch a bot.send_message method.

        Args:
            bot: bot to patch
        """
        old_send_method = bot.send_message

        def real_send_message(*args, **kwargs) -> Message:
            """
            Remember all the sent messages.
            """
            msg = old_send_method(*args, **kwargs)
            cls.remember_msg(msg)
            return msg

        bot.send_message = real_send_message

    @classmethod
    def remove_messages(cls, context) -> None:
        """
        Remove not actual messages.

        Args:
            context: bot context
        """
        for msg in MessageForRemoval.iterate_and_remove():
            try:
                context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)
            except BadRequest:
                pass
