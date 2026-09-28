"""Сущность «Показатель»: справочник величин и настраиваемые нормы."""

from math import isfinite


def default_metrics() -> list[dict]:
    """Вернуть новый справочник учебных, а не нормативных порогов."""
    return [
        {"id": "temperature", "name": "Температура", "unit": "°C",
         "minimum": 18.0, "maximum": 24.0},
        {"id": "humidity", "name": "Влажность", "unit": "%",
         "minimum": 40.0, "maximum": 60.0},
        {"id": "leak", "name": "Протечка", "unit": "0/1",
         "minimum": 0.0, "maximum": 0.0},
    ]


def validate_metric(metric: dict) -> None:
    """Проверить название, единицу и конечные упорядоченные границы."""
    if not isinstance(metric, dict):
        raise ValueError("Показатель должен быть словарём.")
    for field in ("id", "name", "unit"):
        if not isinstance(metric.get(field), str) or not metric[field].strip():
            raise ValueError(f"Поле показателя {field} не должно быть пустым.")
    for field in ("minimum", "maximum"):
        value = metric.get(field)
        if type(value) not in (int, float) or not isfinite(value):
            raise ValueError("Границы показателя должны быть конечными.")
    if metric["minimum"] > metric["maximum"]:
        raise ValueError("Минимальная граница больше максимальной.")
    if metric["id"] == "leak" and (
        metric["minimum"] != 0 or metric["maximum"] != 0
    ):
        raise ValueError("Для протечки нормой всегда является 0.")


def get_metric(metrics: list[dict], metric_id: str) -> dict:
    """Найти показатель по стабильному идентификатору."""
    for metric in metrics:
        if metric["id"] == metric_id:
            return metric
    raise ValueError(f"Показатель {metric_id} не найден.")


def update_limits(metric: dict, minimum: float, maximum: float) -> None:
    """Изменить норму для будущих проверок, сохраняя старые измерения."""
    candidate = {**metric, "minimum": minimum, "maximum": maximum}
    validate_metric(candidate)
    metric.update(candidate)


def analyze_metric(value: float, minimum: float, maximum: float) -> dict:
    """Оценить показатель; границы диапазона входят в норму."""
    numbers = (value, minimum, maximum)
    if any(type(n) not in (int, float) or not isfinite(n) for n in numbers):
        raise ValueError("Показание и границы должны быть конечными числами.")
    if minimum > maximum:
        raise ValueError("Минимальная граница больше максимальной.")
    if value < minimum:
        position, deviation = "below", minimum - value
    elif value > maximum:
        position, deviation = "above", value - maximum
    else:
        position = "normal"
        deviation = abs(value - (minimum + maximum) / 2)
    return {
        "value": value, "minimum": minimum, "maximum": maximum,
        "normal": position == "normal", "position": position,
        "deviation": round(deviation, 2),
    }
