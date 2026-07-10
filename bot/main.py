import logging
from datetime import time as dt_time

from telegram.ext import Application, CommandHandler

from . import config, database, handlers
from .scheduler import daily_reschedule, schedule_all_for_today

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def _post_init(application: Application) -> None:
    schedule_all_for_today(application)
    application.job_queue.run_daily(
        daily_reschedule,
        time=dt_time(
            config.DAILY_RESCHEDULE_HOUR, config.DAILY_RESCHEDULE_MINUTE, tzinfo=config.TZ
        ),
        name="daily-scheduler",
    )
    logger.info("Scheduler initialized.")


def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

    database.init_db()

    application = (
        Application.builder().token(config.BOT_TOKEN).post_init(_post_init).build()
    )

    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("stop", handlers.stop))
    application.add_handler(CommandHandler("now", handlers.now))
    application.add_handler(CommandHandler("help", handlers.help_command))

    logger.info("Starting bot...")
    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
