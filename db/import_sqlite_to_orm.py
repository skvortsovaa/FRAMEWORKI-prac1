"""ПР7 читается через sqlite3; запись в целевую базу только через ORM."""

from contextlib import closing
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from db.database import get_connection
from db.import_json import COLUMNS
from reports_web.models import Metric, Reading, Report
from rooms_web.models import Room
from sensors_web.models import Sensor


MODELS = {"rooms": Room, "sensors": Sensor, "metrics": Metric,
          "reports": Report, "readings": Reading}


def read_source(source):
    """Источник открывается только на чтение, в согласованной транзакции."""
    source = Path(source).resolve()
    target = Path(settings.DATABASES["default"]["NAME"]).resolve()
    if source == target:
        raise ValueError("Источник и целевая база должны различаться.")
    with closing(get_connection(source, read_only=True)) as connection:
        connection.execute("BEGIN")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Исходная база повреждена.")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("В исходной базе нарушены внешние ключи.")
        return {
            table: [dict(row) for row in connection.execute(
                f"SELECT {columns} FROM {table} ORDER BY id"
            )] for table, columns in COLUMNS.items()
        }


def normalize(model, row):
    """0/1 проверяются до bool(); время ПР7 трактуется как московское."""
    row = dict(row)
    for field in model._meta.fields:
        name = field.attname
        # ПР10 добавляет slug и GeneratedField, которых нет в источнике ПР7.
        if name not in row:
            continue
        value = row[name]
        if field.get_internal_type() == "BooleanField" and value is not None:
            if type(value) is not int or value not in (0, 1):
                raise ValueError(f"{model.__name__}.{name}: ожидается 0/1.")
            row[name] = bool(value)
        elif field.get_internal_type() == "DateTimeField":
            value = datetime.fromisoformat(value)
            row[name] = (timezone.make_aware(value) if timezone.is_naive(value)
                         else value)
    return row


def import_source(source=None, *, update=False):
    """Атомарный повторяемый импорт с защитой изменённых целевых записей."""
    rows = read_source(source or settings.SMARTSPACE_DB_PATH)
    with transaction.atomic():
        for table, model in MODELS.items():
            for raw in rows[table]:
                values = normalize(model, raw)
                existing = model.objects.filter(pk=values["id"]).first()
                if existing is not None:
                    if all(getattr(existing, key) == value
                           for key, value in values.items()):
                        continue
                    if not update:
                        raise ValueError(
                            f"{table}/{values['id']} уже изменён. "
                            "Для осознанного обновления используйте --update."
                        )
                obj = model(**values) if existing is None else existing
                for key, value in values.items():
                    setattr(obj, key, value)
                obj.full_clean()
                obj.save()
        # Проверяем не только количество, но и каждое поле и внешний ключ.
        for table, model in MODELS.items():
            for raw in rows[table]:
                values = normalize(model, raw)
                actual = model.objects.get(pk=values["id"])
                if any(getattr(actual, key) != value
                       for key, value in values.items()):
                    raise ValueError(f"Не совпадают данные {table}.")
    return {table: len(records) for table, records in rows.items()}
