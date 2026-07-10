import sqlite3
from datetime import datetime, timezone

from . import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id INTEGER PRIMARY KEY,
                joined_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )


def add_subscriber(chat_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO subscribers (chat_id, joined_at, active)
            VALUES (?, ?, 1)
            ON CONFLICT(chat_id) DO UPDATE SET active = 1
            """,
            (chat_id, datetime.now(timezone.utc).isoformat()),
        )


def remove_subscriber(chat_id: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE subscribers SET active = 0 WHERE chat_id = ?", (chat_id,))


def is_subscribed(chat_id: int) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT active FROM subscribers WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return bool(row and row[0])


def get_active_subscribers() -> list[int]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT chat_id FROM subscribers WHERE active = 1"
        ).fetchall()
        return [row[0] for row in rows]
