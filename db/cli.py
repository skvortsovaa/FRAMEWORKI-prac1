"""Просмотр именованных запросов и диагностика SQL из терминала."""

import argparse
from contextlib import closing
import json
from pathlib import Path

from db.database import DB_PATH, execute_query, get_connection, load_queries


def main():
    parser = argparse.ArgumentParser(description="SQL-запросы SmartSpace")
    parser.add_argument("--database", type=Path, default=DB_PATH)
    parser.add_argument("--list", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--query", choices=list(load_queries()))
    group.add_argument("--sql")
    parser.add_argument("--params", default="[]")
    args = parser.parse_args()
    if args.list:
        print("\n".join(load_queries()))
        return
    parameters = json.loads(args.params)
    with closing(get_connection(args.database, read_only=True)) as conn:
        cursor = (execute_query(conn, args.query, parameters) if args.query
                  else conn.execute(args.sql or "PRAGMA database_list",
                                    parameters))
        print(json.dumps([dict(row) for row in cursor.fetchall()],
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
