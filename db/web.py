"""Общие проверки параметров и безопасное чтение SQLite для веба."""

from contextlib import contextmanager
from datetime import date
from functools import wraps
import math
import sqlite3

from django.conf import settings

from db.database import get_connection
from homepage.views import data_unavailable

STATUSES = ("НОРМА", "ПРЕДУПРЕЖДЕНИЕ", "АВАРИЯ", "НЕТ ДАННЫХ")


def database_page(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except (sqlite3.Error, OSError):
            return data_unavailable(request)
    return wrapped


@contextmanager
def connection():
    conn = get_connection(settings.SMARTSPACE_DB_PATH, read_only=True)
    try:
        yield conn
    finally:
        conn.close()


def integer(value, minimum=0, maximum=9223372036854775807):
    if not value.isascii() or not value.isdecimal():
        raise ValueError("Введите целое число из цифр 0–9.")
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"Допустимый диапазон: {minimum}–{maximum}.")
    return number


def area_value(value):
    number = float(value.replace(",", "."))
    if not math.isfinite(number) or number < 0:
        raise ValueError("Площадь должна быть неотрицательным числом.")
    return number


def date_value(value):
    if value and (len(value) != 10 or date.fromisoformat(value).isoformat()
                  != value):
        raise ValueError("Выберите дату в формате ГГГГ-ММ-ДД.")
    return value
