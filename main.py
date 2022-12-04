import json
import logging
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


logger = logging.getLogger(__name__)


def init_logging():
    logging.basicConfig(
        filename=config.LOG_FILE,
        encoding='utf-8',
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


class SetReminderStates(int, Enum):
    NAME = 1
    TIME = 3
    TEXT = 5


@dataclass
class Reminder:
    name: str = None
    time: str = None
    days_interval: tuple = None
    text: str = None
    run_once: bool = False


# @handle_any_error
# @auth
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Привет! Я - dastin, вызови меню либо /help, чтобы посмотреть, что я умею 😉"
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


# @handle_any_error
# @auth
def set_(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(chat_id=update.message.chat_id, text='Введи название напоминания')

    return SetReminderStates.NAME


# @handle_any_error
def set_name(update: Update, context: CallbackContext) -> int:
    reminder_name = update.message.text

    user_id = update.message.from_user.id

    if is_job_exists(reminder_name, context):
        context.bot.send_message(chat_id=update.message.chat_id, text='Напоминалка с таким названием уже есть, попробуй другое название')
        return SetReminderStates.NAME

    context.user_data[user_id] = Reminder(name=reminder_name)

    text = '\n'.join([
        'Введи тайминги', '',
        'примеры:',
        '10:29 пн-пт (запускать в 10:29 каждый день с пн по пт)',
        '23:59 пн (запускать в 23:59 каждый пн)',
    ])

    context.bot.send_message(chat_id=update.message.chat_id, text=text)

    return SetReminderStates.TIME


# @handle_any_error
def save_reminder_time(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    tz = pytz.timezone('Europe/Moscow')

    user_id = update.message.from_user.id

    timing = text.split()
    time_, interval = timing[0], None
    if len(timing) == 2:
        time_, interval = timing

    hour, minute = time_.split(':')
    hour = int(hour)
    minute = int(minute)
    context.user_data[user_id].time = datetime.time(hour=hour, minute=minute, tzinfo=tz)

    if interval is None:
        context.user_data[user_id].run_once = True
        context.bot.send_message(chat_id=update.message.chat_id, text='Введи текст напоминалки')
        return SetReminderStates.TEXT

    day_to_num = {'пн': 0, 'вт': 1, 'ср': 2, 'чт': 3, 'пт': 4, 'сб': 5, 'вс': 6}

    interval = interval.split('-')
    if len(interval) == 1:
        day_num = day_to_num[interval[0]]
        context.user_data[user_id].days_interval = (day_num,)
        context.bot.send_message(chat_id=update.message.chat_id, text='Введи текст напоминалки, который нужно показать всем')
        return SetReminderStates.TEXT

    beg, end = day_to_num[interval[0]], day_to_num[interval[1]]
    context.user_data[user_id].days_interval = (beg, end)

    context.bot.send_message(chat_id=update.message.chat_id, text='Введи текст напоминалки')
    return SetReminderStates.TEXT


def notifyer(reminder: Reminder, context: CallbackContext):
    context.bot.send_message(chat_id=config.TEAM_CHAT_ID, text=reminder.text)


# @handle_any_error
def save_reminder_info(update: Update, context: CallbackContext) -> int:
    reminder_text = update.message.text

    user_id = update.message.from_user.id

    reminder: Reminder = context.user_data[user_id]
    reminder.text = reminder_text

    name = reminder.name
    time = reminder.time
    days = reminder.days_interval

    notify = partial(notifyer, reminder)

    if reminder.run_once:
        context.job_queue.run_once(notify, time, name=name, context=update)
    else:
        context.job_queue.run_daily(notify, time, name=name, days=days, context=update)

    context.bot.send_message(chat_id=update.message.chat_id, text='Напоминание сохранено 🙌')
    return ConversationHandler.END


# @handle_any_error
def fallback(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(chat_id=update.message.chat_id, text='я сломався, попробуй сначала 😅')

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


def show_all_tasks(update: Update, context: CallbackContext):
    when_q_is_empty = 'Напоминаний пока нет'
    text = '\n'.join([f'{j.name}, ближайший запуск: {j.next_t}' for j in context.job_queue.jobs()]) or when_q_is_empty
    context.bot.send_message(chat_id=update.message.chat_id, text=text)


def remove_task_by_name(update: Update, context: CallbackContext):
    name = context.args[0]
    jobs = context.job_queue.get_jobs_by_name(name)

    if not jobs:
        context.bot.send_message(chat_id=update.message.chat_id, text=f'Нет напоминаний с названием {name}')
        return

    for job in jobs:
        job.schedule_removal()

    context.bot.send_message(chat_id=update.message.chat_id, text=f'Напоминание {name} удалено')


handle = ConversationHandler(
    entry_points=[CommandHandler('set', set_)],
    states={
        SetReminderStates.NAME: [MessageHandler(Filters.text, set_name)],
        SetReminderStates.TIME: [MessageHandler(Filters.text, save_reminder_time)],
        SetReminderStates.TEXT: [MessageHandler(Filters.text, save_reminder_info)],
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
    logger.error(message)


def main() -> None:
    updater = Updater(config.BOTTOKEN_DASTIN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help_))
    dispatcher.add_handler(CommandHandler('all', show_all_tasks))
    dispatcher.add_handler(CommandHandler('rm', remove_task_by_name))
    dispatcher.add_handler(handle)

    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
