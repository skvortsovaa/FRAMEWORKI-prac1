"""Проверяемый транзакционный перенос JSON в самостоятельную SQLite."""

import argparse
from contextlib import closing
from pathlib import Path

from db.database import BASE_DIR, DB_PATH, get_connection, initialize_database
from storage import COLLECTIONS, JOURNAL, decode_data, encode_data, read_json

# Имена и столбцы заданы кодом, а значения всегда передаются через ?.
COLUMNS = {
    "rooms": "id, name, floor, area",
    "sensors": "id, room_id, active, battery",
    "metrics": "id, name, unit, minimum, maximum",
    "reports": (
        "id, room_id, room_name, checked_at, sensor_active, battery, "
        "temperature_value, temperature_minimum, temperature_maximum, "
        "temperature_normal, humidity_value, humidity_minimum, "
        "humidity_maximum, humidity_normal, leak_detected, status"
    ),
    "readings": (
        "id, sensor_id, metric_id, report_id, measured_at, value, "
        "minimum, maximum, status"
    ),
}


def prepare_rows(directory):
    """Проверить все JSON и общие ссылки до изменения базы."""
    directory = Path(directory)
    if (directory / JOURNAL).exists():
        raise ValueError("Сначала восстановите JSON в консольной версии.")
    raw = {name: read_json(directory / f"{name}.json")
           for name in COLLECTIONS}
    raw = encode_data(decode_data(raw))
    rows = {}
    for table, columns in COLUMNS.items():
        records = []
        for source in raw[table]:
            row = dict(source)
            if table == "reports":
                for metric in ("temperature", "humidity"):
                    analysis = row[metric]
                    for field in ("value", "minimum", "maximum", "normal"):
                        row[f"{metric}_{field}"] = (
                            analysis[field] if analysis else None
                        )
            values = tuple(int(row[key]) if type(row[key]) is bool
                           else row[key] for key in columns.split(", "))
            records.append(values)
        rows[table] = records
    return rows


def import_data(directory=None, database=None, *, replace=False):
    """Повторный одинаковый импорт ничего не меняет; иной требует --replace."""
    rows = prepare_rows(directory or BASE_DIR / "data")
    path = initialize_database(database or DB_PATH)
    with closing(get_connection(path)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            present = {
                table: [tuple(row) for row in conn.execute(
                    f"SELECT {columns} FROM {table} ORDER BY id"
                )] for table, columns in COLUMNS.items()
            }
            identical = all(present[t] == sorted(rows[t], key=lambda r: r[0])
                            for t in COLUMNS)
            if not identical:
                if any(present.values()) and not replace:
                    raise ValueError(
                        "База отличается от JSON. Для явной замены: --replace."
                    )
                if replace:
                    for table in reversed(COLUMNS):
                        conn.execute(f"DELETE FROM {table}")
                for table, columns in COLUMNS.items():
                    placeholders = ", ".join("?" for _ in columns.split(", "))
                    conn.executemany(
                        f"INSERT INTO {table} ({columns}) "
                        f"VALUES ({placeholders})", rows[table],
                    )
            if conn.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Импорт нарушает внешние ключи.")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {name: len(records) for name, records in rows.items()}


def main():
    parser = argparse.ArgumentParser(description="Перенести данные JSON")
    parser.add_argument("--source", type=Path, default=BASE_DIR / "data")
    parser.add_argument("--database", type=Path, default=DB_PATH)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    for name, count in import_data(args.source, args.database,
                                   replace=args.replace).items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
