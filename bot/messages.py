"""Loads the reminder quotes the bot sends at random.

The actual text lives in bot/quotes.txt, not here, so anyone can add, edit,
or delete quotes without touching any code: open quotes.txt, add a new
block of text wherever you like, and separate it from its neighbors with a
line containing only "---". No escaping or special formatting needed.
"""

import random
from pathlib import Path

QUOTES_PATH = Path(__file__).resolve().parent / "quotes.txt"


def _load_quotes() -> list[str]:
    raw = QUOTES_PATH.read_text(encoding="utf-8")
    return [block.strip() for block in raw.split("\n---\n") if block.strip()]


REMINDERS: list[str] = _load_quotes()


def get_random_message(exclude: str | None = None) -> str:
    """Return a random quote, avoiding an immediate repeat when possible."""
    choices = REMINDERS
    if exclude and len(REMINDERS) > 1:
        choices = [m for m in REMINDERS if m != exclude]
    return random.choice(choices)
