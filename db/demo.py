"""Отдельная копия SQLite для повторяемых сценариев защиты ПР7."""

import argparse
from contextlib import closing

from db.database import BASE_DIR, DB_PATH, get_connection

DEMO_PATH = BASE_DIR / ".demo" / "smartspace.sqlite"


def main():
    parser = argparse.ArgumentParser(description="Демонстрационная копия БД")
    parser.add_argument("action", choices=("reset", "rename", "disable"))
    args = parser.parse_args()
    DEMO_PATH.parent.mkdir(exist_ok=True)
    if args.action == "reset":
        with closing(get_connection(DB_PATH, read_only=True)) as source:
            with closing(get_connection(DEMO_PATH)) as target:
                source.backup(target)
    else:
        if not DEMO_PATH.exists():
            parser.error("Сначала выполните python -m db.demo reset")
        with closing(get_connection(DEMO_PATH)) as conn, conn:
            if args.action == "rename":
                conn.execute("UPDATE rooms SET name = ? WHERE id = ?",
                             ("Серверная №1 — демо SQLite", 1))
            else:
                conn.execute("UPDATE sensors SET active = ? WHERE room_id = ?",
                             (0, 2))
    print(DEMO_PATH)


if __name__ == "__main__":
    main()
