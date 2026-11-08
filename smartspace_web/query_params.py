"""Параметры HTTP-запросов без зависимости от прежнего SQL-слоя."""

from datetime import date
from functools import wraps
import math

from django.db import DatabaseError

from homepage.views import data_unavailable


def database_page(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except DatabaseError:
            return data_unavailable(request)
    return wrapped


def integer(value, minimum=0, maximum=9223372036854775807):
    if not value.isascii() or not value.isdecimal() or len(value) > 19:
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
    if not value:
        return None
    parsed = date.fromisoformat(value)
    if len(value) != 10 or parsed.isoformat() != value:
        raise ValueError("Выберите дату в формате ГГГГ-ММ-ДД.")
    return parsed
