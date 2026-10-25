"""Пути, соединения SQLite и именованные SQL-запросы ПР7."""

import argparse
from contextlib import closing
from pathlib import Path
import re
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "smartspace.sqlite"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"
QUERIES_PATH = BASE_DIR / "sql" / "queries.sql"


def get_connection(path=None, *, read_only=False):
    """Row даёт доступ по именам; каждое соединение проверяет FK."""
    path = Path(path or DB_PATH).resolve()
    if read_only:
        conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        conn.execute("PRAGMA query_only = ON")
    else:
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(path=None):
    """Повторное применение IF NOT EXISTS сохраняет таблицы и данные."""
    path = Path(path or DB_PATH).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(get_connection(path)) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    return path


def load_queries():
    """Единственный источник текста запросов для сайта и CLI."""
    source = QUERIES_PATH.read_text(encoding="utf-8")
    parts = re.split(r"^-- name: ([a-z_]+)\s*$", source, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def execute_query(conn, name, parameters=()):
    """Значения передаются отдельно от текста выбранного запроса."""
    return conn.execute(load_queries()[name], parameters)


def main():
    parser = argparse.ArgumentParser(description="Создать схему SmartSpace")
    parser.add_argument("--database", type=Path, default=DB_PATH)
    args = parser.parse_args()
    print(initialize_database(args.database))


if __name__ == "__main__":
    main()
