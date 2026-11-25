"""Class mode storage (optional). Stores only {class code, misconception id, topic, time}.

Disabled entirely when DATABASE_URL is unset. Run `python -m redline.db` to migrate;
the app also applies the idempotent schema on first use.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L
_migrated = False


class DBUnavailable(Exception):
    pass


def enabled() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def _conn():
    if not enabled():
        raise DBUnavailable("DATABASE_URL is not set")
    import psycopg

    global _migrated
    try:
        conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=8, autocommit=True)
    except psycopg.Error as e:
        raise DBUnavailable(type(e).__name__) from e
    if not _migrated:
        conn.execute(SCHEMA)
        _migrated = True
    return conn


def new_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(6))


def create_class(name: str) -> str:
    with _conn() as c:
        for _ in range(5):
            code = new_code()
            if c.execute("insert into classes (code, name) values (%s, %s) on conflict do nothing", (code, name)).rowcount:
                return code
    raise DBUnavailable("could not allocate a class code")


def class_name(code: str) -> str | None:
    with _conn() as c:
        row = c.execute("select name from classes where code = %s", (code,)).fetchone()
    return row[0] if row else None


def add_event(code: str, misconception_id: str, topic: str) -> bool:
    with _conn() as c:
        if not c.execute("select 1 from classes where code = %s", (code,)).fetchone():
            return False
        c.execute(
            "insert into misconception_events (class_code, misconception_id, topic) values (%s, %s, %s)",
            (code, misconception_id, topic),
        )
    return True


def summary(code: str, days: int = 14) -> tuple[int, list[tuple[str, int]]]:
    with _conn() as c:
        rows = c.execute(
            "select misconception_id, count(*) from misconception_events "
            "where class_code = %s and created_at > now() - make_interval(days => %s) "
            "group by 1 order by 2 desc, 1",
            (code, days),
        ).fetchall()
    return sum(n for _, n in rows), [(m, n) for m, n in rows]


def health() -> str:
    if not enabled():
        return "disabled"
    try:
        with _conn() as c:
            c.execute("select 1")
        return "ok"
    except Exception:  # noqa: BLE001 - health must never raise
        return "error"


if __name__ == "__main__":
    with _conn():
        print("schema applied")
