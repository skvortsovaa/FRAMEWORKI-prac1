"""Общие проверки полей объектов предметной области."""

from datetime import datetime
from math import isfinite


def require_text(value: str, field: str) -> None:
    """Проверить непустую строку без изменения исходного значения."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Поле {field} должно быть непустой строкой.")


def require_number(value: float, field: str) -> None:
    """Отклонить bool, NaN, бесконечность и нечисловые значения."""
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError(f"Поле {field} должно быть конечным числом.")


def require_datetime(value: str) -> None:
    """Проверить дату или время в ISO-формате, используемом в ПР2."""
    require_text(value, "время")
    try:
        datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Некорректное время измерения или отчёта.") from error
