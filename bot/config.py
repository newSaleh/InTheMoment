import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "bot_data.db")

TZ_NAME = os.getenv("TZ_NAME", "Asia/Riyadh")
TZ = ZoneInfo(TZ_NAME)

# Reminders only fire inside this daily window (local to TZ_NAME).
ACTIVE_HOUR_START = int(os.getenv("ACTIVE_HOUR_START", "9"))
ACTIVE_HOUR_END = int(os.getenv("ACTIVE_HOUR_END", "23"))

# How many random reminders each subscriber gets per day.
MIN_DAILY_REMINDERS = int(os.getenv("MIN_DAILY_REMINDERS", "2"))
MAX_DAILY_REMINDERS = int(os.getenv("MAX_DAILY_REMINDERS", "3"))

# Minimum spacing enforced between two reminders on the same day.
MIN_GAP_MINUTES = int(os.getenv("MIN_GAP_MINUTES", "60"))

# Time of day (local to TZ_NAME) at which tomorrow's random schedule is drawn.
DAILY_RESCHEDULE_HOUR = int(os.getenv("DAILY_RESCHEDULE_HOUR", "0"))
DAILY_RESCHEDULE_MINUTE = int(os.getenv("DAILY_RESCHEDULE_MINUTE", "5"))
