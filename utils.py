"""Повторный запрос при ошибках числового ввода."""

from math import isfinite


def input_int(prompt: str) -> int:
    """Запрашивать ввод до получения целого числа."""
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Введите целое число.")


def input_float(prompt: str) -> float:
    """Прочитать конечное число; допускается десятичная запятая."""
    while True:
        try:
            value = float(input(prompt).replace(",", "."))
            if not isfinite(value):
                raise ValueError
            return value
        except ValueError:
            print("Введите конечное число, например 25.5.")
