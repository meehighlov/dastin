from functools import wraps
from config import config
from telegram import Update
from telegram.ext import  CallbackContext


def auth(handler):

    @wraps(handler)
    def check_username(update: Update, context: CallbackContext):

        username = update.message.from_user.name
        if username not in config.ALLOWED_USERNAMES_LIST:
            return

        return handler(update, context)

    return check_username
