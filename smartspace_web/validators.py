"""Проверки полей ORM, сериализуемые в миграциях."""

import math

from django.core.exceptions import ValidationError


def finite_number(value):
    if not math.isfinite(value):
        raise ValidationError("Введите конечное число.")


def nonblank_text(value):
    if not value.strip():
        raise ValidationError("Строка не должна состоять из пробелов.")


def positive_number(value):
    finite_number(value)
    if value <= 0:
        raise ValidationError("Число должно быть больше нуля.")
