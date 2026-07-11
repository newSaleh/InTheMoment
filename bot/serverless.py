"""Stateless entry point meant to be run periodically by GitHub Actions.

Unlike bot/main.py (a long-running polling process), this script does one
pass and exits: it fetches any new Telegram updates since last run, handles
commands, tops up each subscriber's random daily schedule, sends whatever
reminders are due, and persists everything to data/state.json so the next
run (a fresh GitHub Actions job, minutes or hours later) can pick up where
this one left off. The workflow that calls this script is responsible for
committing the updated state file back to the repository.
"""

import json
import os
import random
import urllib.error
import urllib.request
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from bot.messages import get_random_message

def _env(name: str, default: str) -> str:
    # GitHub Actions sets the env var to an empty string when the
    # referenced `vars.*` context key doesn't exist, rather than leaving
    # it unset, so a plain os.environ.get(name, default) wouldn't fall
    # back correctly.
    return os.environ.get(name) or default


BOT_TOKEN = os.environ["BOT_TOKEN"]
TZ = ZoneInfo(_env("TZ_NAME", "Asia/Riyadh"))

ACTIVE_HOUR_START = int(_env("ACTIVE_HOUR_START", "9"))
ACTIVE_HOUR_END = int(_env("ACTIVE_HOUR_END", "23"))
MIN_DAILY_REMINDERS = int(_env("MIN_DAILY_REMINDERS", "2"))
MAX_DAILY_REMINDERS = int(_env("MAX_DAILY_REMINDERS", "3"))
MIN_GAP_MINUTES = int(_env("MIN_GAP_MINUTES", "60"))

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "state.json"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/{{method}}"

WELCOME = (
    "أهلًا بك 🌿\n\n"
    "أنا بوت صغير مهمتي الوحيدة أن أذكّرك، بين الحين والآخر، بأن تعيش اللحظة "
    "التي أنت فيها الآن، وبأننا جميعًا فانون عاجلًا أم آجلًا. أرسل لك اقتباساتٍ "
    "من كتاب «التأملات» لماركوس أوريليوس.\n\n"
    "سأرسل لك تذكيرين أو ثلاثة يوميًا، في أوقات عشوائية غير متوقعة.\n"
    "(ملاحظة: هذا البوت يعمل عبر فحص دوري كل بضع دقائق، فقد يتأخر ردي "
    "على أوامرك قليلًا وليس فوريًا.)\n\n"
    "الأوامر المتاحة:\n"
    "/now — أرسل لي تذكيرًا الآن\n"
    "/stop — أوقف التذكيرات\n"
    "/help — عرض هذه الرسالة"
)
STOP_MSG = "تم إيقاف التذكيرات. يمكنك إعادة تفعيلها في أي وقت عبر /start 🌙"


def _call(method: str, **params):
    url = API_URL.format(method=method)
    data = json.dumps(params).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        print(f"Telegram API call failed ({method}): {exc}")
        return {"ok": False}


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"offset": 0, "subscribers": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def pick_times_for_day(now: datetime) -> list[datetime]:
    """Pick 2-3 well-spaced random timestamps within today's active window."""
    today = now.astimezone(TZ).date()
    window_start = datetime.combine(today, dt_time(ACTIVE_HOUR_START), tzinfo=TZ)
    window_end = datetime.combine(today, dt_time(ACTIVE_HOUR_END), tzinfo=TZ)

    effective_start = max(now, window_start)
    if effective_start >= window_end:
        return []

    span_minutes = int((window_end - effective_start).total_seconds() // 60)
    count = random.randint(MIN_DAILY_REMINDERS, MAX_DAILY_REMINDERS)
    while count > 1 and span_minutes < MIN_GAP_MINUTES * (count - 1):
        count -= 1
    if count < 1 or span_minutes <= 0:
        return []

    offsets = sorted(random.sample(range(span_minutes + 1), k=min(count, span_minutes + 1)))
    times: list[datetime] = []
    last: datetime | None = None
    for offset in offsets:
        candidate = effective_start + timedelta(minutes=offset)
        if last is not None and (candidate - last) < timedelta(minutes=MIN_GAP_MINUTES):
            candidate = last + timedelta(minutes=MIN_GAP_MINUTES)
        if candidate >= window_end:
            continue
        times.append(candidate)
        last = candidate
    return times


def handle_updates(state: dict, now: datetime) -> None:
    result = _call("getUpdates", offset=state["offset"] + 1, timeout=0)
    if not result.get("ok"):
        return

    for update in result.get("result", []):
        state["offset"] = max(state["offset"], update["update_id"])
        message = update.get("message")
        if not message or "text" not in message:
            continue

        chat_id = str(message["chat"]["id"])
        text = message["text"].strip()

        if text.startswith("/start"):
            sub = state["subscribers"].setdefault(chat_id, {})
            sub["active"] = True
            sub.setdefault("schedule_date", None)
            sub.setdefault("today_times", [])
            sub.setdefault("sent_times", [])
            sub.setdefault("last_message", None)
            _call("sendMessage", chat_id=int(chat_id), text=WELCOME)
        elif text.startswith("/stop"):
            sub = state["subscribers"].get(chat_id)
            if sub:
                sub["active"] = False
            _call("sendMessage", chat_id=int(chat_id), text=STOP_MSG)
        elif text.startswith("/now"):
            _call("sendMessage", chat_id=int(chat_id), text=get_random_message())
        elif text.startswith("/help"):
            _call("sendMessage", chat_id=int(chat_id), text=WELCOME)


def refresh_daily_schedules(state: dict, now: datetime) -> None:
    today_str = now.astimezone(TZ).date().isoformat()
    for sub in state["subscribers"].values():
        if not sub.get("active"):
            continue
        if sub.get("schedule_date") != today_str:
            times = pick_times_for_day(now)
            sub["schedule_date"] = today_str
            sub["today_times"] = [t.isoformat() for t in times]
            sub["sent_times"] = []


def send_due_reminders(state: dict, now: datetime) -> None:
    for chat_id, sub in state["subscribers"].items():
        if not sub.get("active"):
            continue
        for t_str in sub.get("today_times", []):
            if t_str in sub.get("sent_times", []):
                continue
            if datetime.fromisoformat(t_str) > now:
                continue
            text = get_random_message(exclude=sub.get("last_message"))
            response = _call("sendMessage", chat_id=int(chat_id), text=text)
            if response.get("ok"):
                sub["sent_times"].append(t_str)
                sub["last_message"] = text


def main() -> None:
    now = datetime.now(TZ)
    state = load_state()
    handle_updates(state, now)
    refresh_daily_schedules(state, now)
    send_due_reminders(state, now)
    save_state(state)


if __name__ == "__main__":
    main()
