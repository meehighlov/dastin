import random
import datetime

import pytz
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from auth import auth

from config import config
from exceptions import handle_any_error



@handle_any_error
@auth
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


def is_job_exists(name: str, context: CallbackContext) -> bool:
    return not context.job_queue.get_jobs_by_name(name)


def unset(update: Update, context: CallbackContext) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Timer successfully cancelled!' if job_removed else 'You have no active timer.'
    update.message.reply_text(text)


@handle_any_error
@auth
def schedule(update: Update, context: CallbackContext):
    tz = pytz.timezone('Europe/Moscow')
    job_name = context.args[0]
    if is_job_exists(job_name):
        context.bot.send_message(chat_id=update.message.chat_id, text='Напоминание с таким названием уже существует 🤔')
        return

    h, m = context.args[1].split(':')
    days_interval = context.args[3]
    text = context.args[4]

    time = datetime.time(hour=int(h), minute=int(m), tzinfo=tz)
    context.job_queue.run_daily(notify_assignees, time, name=job_name, days=tuple(range(5)), context=update)

    context.bot.send_message(chat_id=update.message.chat_id, text='Уведомления о дайли включены 😉')


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


def main() -> None:
    updater = Updater(config.BOTTOKEN_DASTIN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))
    dispatcher.add_handler(CommandHandler("set", schedule))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
