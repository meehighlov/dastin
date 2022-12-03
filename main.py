import json
import traceback
from dataclasses import dataclass
from enum import Enum
from functools import partial
import random
import datetime

import pytz
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters
from auth import auth

from config import config



class TextFilter(Filters.text):
    
    def filter(self, message):
        pass
    

class SetReminderStates(int, Enum):
    NAME = 1
    MESSAGE_ABOUT_TIME = 2
    TIME = 3
    MESSAGE_ABOUT_TEXT = 4
    TEXT = 5
    SUCCESS = 6


@dataclass
class Reminder:
    name: str = None
    time: str = None
    days_interval: tuple = None
    text: str = None


# @handle_any_error
# @auth
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "I'm Dastin, events reminder for daservice team, tell me about your events"
    )


# @handle_any_error
# @auth
def help_(update: Update, context: CallbackContext):
    all_commands = [
        '/set - set new reminder',
        '/rm - remove exist reminder',
        '/all - show exist reminders',
    ]

    text = '\n'.join(all_commands)

    context.bot.send_message(chat_id=update.message.chat_id, text=text)


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def is_job_exists(name: str, context: CallbackContext) -> bool:
    return len(context.job_queue.get_jobs_by_name(name)) > 0


def unset(update: Update, context: CallbackContext) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Timer successfully cancelled!' if job_removed else 'You have no active timer.'
    update.message.reply_text(text)


# @handle_any_error
# @auth
def set_(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(chat_id=update.message.chat_id, text='Введи название напоминания')

    return SetReminderStates.NAME

    # tz = pytz.timezone('Europe/Moscow')
    # job_name = context.args[0]
    # if is_job_exists(job_name):
    #     context.bot.send_message(chat_id=update.message.chat_id, text='Напоминание с таким названием уже существует 🤔')
    #     return

    # h, m = context.args[1].split(':')
    # days_interval = context.args[3]
    # text = context.args[4]

    # time = datetime.time(hour=int(h), minute=int(m), tzinfo=tz)
    # context.job_queue.run_daily(notify_assignees, time, name=job_name, days=tuple(range(5)), context=update)

    # context.bot.send_message(chat_id=update.message.chat_id, text='Уведомления о дайли включены 😉')


# @handle_any_error
def set_name(update: Update, context: CallbackContext) -> int:
    reminder_name = update.message.text

    user_id = update.message.from_user.id

    if is_job_exists(reminder_name, context):
        context.bot.send_message(chat_id=update.message.chat_id, text='Напоминалка с таким названием уже есть, попробуй другое название')
        return SetReminderStates.NAME

    context.user_data[user_id] = Reminder(name=reminder_name)

    return SetReminderStates.MESSAGE_ABOUT_TIME


# @handle_any_error
def show_message_about_time(update: Update, context: CallbackContext) -> int:
    text = '''
        Введи тайминги

        примеры:
        10:29 пн-пт (запускать в 10:29 каждый день с пн по пт)
        23:59 пн (запускать в 23:59 каждый пн)
        23:59 (запустить сегодня в 23:59)
    '''

    context.bot.send_message(chat_id=update.message.chat_id, text=text)

    return SetReminderStates.TIME


# @handle_any_error
def save_reminder_time(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    tz = pytz.timezone('Europe/Moscow')

    time_, interval = text.split()

    user_id = update.message.from_user.id

    hour, minute = time_.split(':')
    hour = int(hour)
    minute = int(minute)
    context.user_data[user_id].time = datetime.time(hour=hour, minute=minute, tzinfo=tz)

    day_to_num = {'пн': 0, 'вт': 1, 'ср': 2, 'чт': 3, 'пт': 4, 'сб': 5, 'вс': 6}

    interval = interval.split('-')
    if len(interval) == 1:
        day_num = day_to_num[interval[0]]
        context.user_data[user_id].days_interval = (day_num,)
        return SetReminderStates.MESSAGE_ABOUT_TEXT

    beg, end = day_to_num[interval[0]], day_to_num[interval[1]]
    context.user_data[user_id].days_interval = (beg, end)

    return SetReminderStates.MESSAGE_ABOUT_TEXT


# @handle_any_error
def show_message_about_text(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(chat_id=update.message.chat_id, text='Введи текст напоминалки')

    return SetReminderStates.TEXT


def notifyer(reminder: Reminder, context: CallbackContext):
    context.bot.send_message(chat_id=config.TEAM_CHAT_ID, text=reminder.text)


# @handle_any_error
def save_reminder_info(update: Update, context: CallbackContext) -> int:
    reminder_text = update.message.text
    
    user_id = update.message.from_user.id

    reminder = context.user_data[user_id]
    reminder.text = reminder_text

    name = reminder.name
    time = reminder.time
    days = reminder.days_interval

    notify = partial(notifyer, reminder)
    context.job_queue.run_daily(notify, time, name=name, days=days, context=update)

    return SetReminderStates.SUCCESS


# @handle_any_error
def show_success(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(chat_id=update.message.chat_id, text='Напоминание сохранено')
    return ConversationHandler.END


# @handle_any_error
def fallback(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(chat_id=update.message.chat_id, text='я сломався, попробуй сначала')

    return ConversationHandler.END


def notify_assignees(context: CallbackContext):
    place = config.TEAM_DAILY_MEETING_URL
    notification_messages = [
        f'Дайлик через 5 минут, предлагаю подключаться уже сейчас 😉 {place}',
        f'Го на дайли 👉👈 {place}',
        f'Проснулись, улыбнулись и идем на дайлик 😌 {place}',
        f'Кто опоздал - тот не успел, а кто успел - тот не опоздал 🐺 дайли тут: {place}',
    ]
    text = random.choice(notification_messages)
    context.bot.send_message(chat_id=config.TEAM_CHAT_ID, text=text)


def notify_about_ts(context: CallbackContext):
    context.bot.send_message(chat_id=config.TEAM_CHAT_ID, text='Самое время проверить таймшиты 🙌')


handle = ConversationHandler(
    entry_points=[CommandHandler('set', set_)],
    states={
        SetReminderStates.NAME: [MessageHandler(Filters.text, set_name)],
        SetReminderStates.MESSAGE_ABOUT_TIME: [MessageHandler(Filters.text, show_message_about_time)],
        SetReminderStates.TIME: [MessageHandler(Filters.text, save_reminder_time)],
        SetReminderStates.MESSAGE_ABOUT_TEXT: [MessageHandler(Filters.text, show_message_about_text)],
        SetReminderStates.TEXT: [MessageHandler(Filters.text, save_reminder_info)],
        SetReminderStates.SUCCESS: [MessageHandler(Filters.text, show_success)],
    },
    fallbacks=[MessageHandler(Filters.text, fallback)],
    allow_reentry=True,
    conversation_timeout=config.CONVERSATION_TIMEOUT,
)


def error_handler(update: Update, context: CallbackContext):
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = json.dumps(update_str, indent=2, ensure_ascii=False) + ' with treaceback: ' + tb_string
    print(message)


def main() -> None:
    updater = Updater(config.BOTTOKEN_DASTIN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_))
    dispatcher.add_handler(handle)

    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
