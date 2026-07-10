import logging
import random
from datetime import datetime, time as dt_time, timedelta

from telegram.ext import Application, ContextTypes

from . import config, database
from .messages import get_random_message

logger = logging.getLogger(__name__)

JOB_PREFIX = "reminder"

# Remembers the last message sent to each chat, in-memory only, so we can
# avoid sending the exact same reminder twice in a row. Resets on restart,
# which is harmless given the size of the message pool.
_last_sent: dict[int, str] = {}


def _job_name(chat_id: int) -> str:
    return f"{JOB_PREFIX}-{chat_id}"


def clear_jobs_for_chat(application: Application, chat_id: int) -> None:
    for job in application.job_queue.get_jobs_by_name(_job_name(chat_id)):
        job.schedule_removal()


def _pick_times_for_today(now: datetime) -> list[datetime]:
    """Pick 2-3 well-spaced random timestamps within today's active window."""
    tz = config.TZ
    today = now.astimezone(tz).date()
    window_start = datetime.combine(today, dt_time(config.ACTIVE_HOUR_START), tzinfo=tz)
    window_end = datetime.combine(today, dt_time(config.ACTIVE_HOUR_END), tzinfo=tz)

    effective_start = max(now, window_start)
    if effective_start >= window_end:
        return []

    span_minutes = int((window_end - effective_start).total_seconds() // 60)
    min_gap = config.MIN_GAP_MINUTES

    count = random.randint(config.MIN_DAILY_REMINDERS, config.MAX_DAILY_REMINDERS)
    while count > 1 and span_minutes < min_gap * (count - 1):
        count -= 1
    if count < 1 or span_minutes <= 0:
        return []

    offsets = sorted(random.sample(range(span_minutes + 1), k=min(count, span_minutes + 1)))

    times: list[datetime] = []
    last: datetime | None = None
    for offset in offsets:
        candidate = effective_start + timedelta(minutes=offset)
        if last is not None and (candidate - last) < timedelta(minutes=min_gap):
            candidate = last + timedelta(minutes=min_gap)
        if candidate >= window_end:
            continue
        times.append(candidate)
        last = candidate
    return times


async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.chat_id
    if not database.is_subscribed(chat_id):
        return
    text = get_random_message(exclude=_last_sent.get(chat_id))
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
        _last_sent[chat_id] = text
    except Exception:
        logger.exception("Failed to send reminder to chat %s", chat_id)


def schedule_today_for_chat(application: Application, chat_id: int) -> int:
    """(Re)schedule this chat's remaining reminders for the rest of today."""
    clear_jobs_for_chat(application, chat_id)
    now = datetime.now(config.TZ)
    times = _pick_times_for_today(now)
    for when in times:
        application.job_queue.run_once(
            send_reminder, when=when, chat_id=chat_id, name=_job_name(chat_id)
        )
    return len(times)


def schedule_all_for_today(application: Application) -> None:
    for chat_id in database.get_active_subscribers():
        n = schedule_today_for_chat(application, chat_id)
        logger.info("Scheduled %d reminder(s) today for chat %s", n, chat_id)


async def daily_reschedule(context: ContextTypes.DEFAULT_TYPE) -> None:
    schedule_all_for_today(context.application)
