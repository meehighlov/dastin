from functools import wraps

from telegram import Update
from telegram.ext import CallbackContext

from logger import log

# TODO add more type hints


def handle_any_error(handler):
    @wraps
    def error_handler(update: Update, context: CallbackContext):
        try:
            return handler(update, context)
        except Exception as e:
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text='Что-то пошло не по плану, не могу выполнить такой запрос 😅'
            )
            log(str(e))

    return error_handler
