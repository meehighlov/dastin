import random
import datetime

import pytz
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

from config import config


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "I'm Dastin, events reminder for daservice team, tell me about your events"
    )


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def unset(update: Update, context: CallbackContext) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Timer successfully cancelled!' if job_removed else 'You have no active timer.'
    update.message.reply_text(text)


def daily_job(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=config.TEAM_CHAT_ID, text='Setting a daily notifications!')
    tz = pytz.timezone('Europe/Moscow')
    time = datetime.time(hour=10, minute=25, tzinfo=tz)
    name = config.TEAM_EVENT_DAILY_NAME
    context.job_queue.run_daily(notify_assignees, time, name=name, days=tuple(range(5)), context=update)


def notify_assignees(context: CallbackContext):
    place = config.TEAM_DAILY_MEETING_URL
    notification_messages = [
        f'Дайлик через 5 минут, предлагаю подключаться уже сейчас 😉 {place}',
        f'Го на дайлик 👉👈 {place}',
        f'Дайлик вот-вот начнется, чекни звук, инетренет-соединие и подключайся 😌 {place}',
    ]
    text = random.choice(notification_messages)
    context.bot.send_message(chat_id=config.TEAM_CHAT_ID, text=text)


def main() -> None:
    updater = Updater(config.BOTTOKEN_DASTIN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))
    dispatcher.add_handler(CommandHandler("set", daily_job))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
