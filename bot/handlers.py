import logging

from telegram import Update
from telegram.ext import ContextTypes

from . import database
from .messages import get_random_message
from .scheduler import clear_jobs_for_chat, schedule_today_for_chat

logger = logging.getLogger(__name__)

WELCOME = (
    "أهلًا بك 🌿\n\n"
    "أنا بوت صغير مهمتي الوحيدة أن أذكّرك، بين الحين والآخر، بأن تعيش اللحظة "
    "التي أنت فيها الآن، وبأننا جميعًا فانون عاجلًا أم آجلًا.\n\n"
    "سأرسل لك تذكيرين أو ثلاثة يوميًا، في أوقات عشوائية غير متوقعة، "
    "لتبقى صادقة كما هي مفاجآت الحياة.\n\n"
    "الأوامر المتاحة:\n"
    "/now — أرسل لي تذكيرًا الآن\n"
    "/stop — أوقف التذكيرات\n"
    "/help — عرض هذه الرسالة"
)

STOP_MSG = "تم إيقاف التذكيرات. يمكنك إعادة تفعيلها في أي وقت عبر /start 🌙"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    already_subscribed = database.is_subscribed(chat_id)
    database.add_subscriber(chat_id)
    scheduled = schedule_today_for_chat(context.application, chat_id)
    await update.message.reply_text(WELCOME)
    if not already_subscribed:
        logger.info("New subscriber %s (%d reminder(s) scheduled today)", chat_id, scheduled)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    database.remove_subscriber(chat_id)
    clear_jobs_for_chat(context.application, chat_id)
    await update.message.reply_text(STOP_MSG)
    logger.info("Chat %s unsubscribed", chat_id)


async def now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_random_message())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME)
