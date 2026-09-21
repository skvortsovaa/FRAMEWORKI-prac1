"""Исходный сценарий ПР1: измерения и оценка состояния помещения."""

from datetime import datetime
from math import isfinite
import random
from uuid import uuid4

from rooms import validate_room


# Учебные пороги, а не универсальные нормативы.
TEMPERATURE_LIMITS = (18.0, 24.0)
HUMIDITY_LIMITS = (40.0, 60.0)


def check_sensor(active: bool, battery: int) -> bool:
    """Доступны ли измерения: датчик включён и батарея не разряжена."""
    return active and battery > 0


def analyze_metric(value: float, minimum: float, maximum: float) -> dict:
    """Оценить показатель; границы диапазона входят в норму."""
    if not all(isfinite(number) for number in (value, minimum, maximum)):
        raise ValueError("Показание и границы должны быть конечными числами.")
    if minimum > maximum:
        raise ValueError("Минимальная граница больше максимальной.")
    if value < minimum:
        position = "below"
        deviation = minimum - value
    elif value > maximum:
        position = "above"
        deviation = value - maximum
    else:
        position = "normal"
        deviation = abs(value - (minimum + maximum) / 2)
    return {
        "value": value,
        "minimum": minimum,
        "maximum": maximum,
        "normal": position == "normal",
        "position": position,
        "deviation": round(deviation, 2),
    }


def get_room_status(
    available: bool, temperature_normal: bool,
    humidity_normal: bool, leak_detected: bool,
) -> str:
    """Определить итоговый статус по правилам из ПР1."""
    if not available:
        return "НЕТ ДАННЫХ"
    elif leak_detected:
        return "АВАРИЯ"
    elif not temperature_normal or not humidity_normal:
        return "ПРЕДУПРЕЖДЕНИЕ"
    else:
        return "НОРМА"


def check_room(room: dict) -> dict:
    """Выполнить одну учебную проверку и вернуть запись для истории."""
    validate_room(room)
    sensor = room["sensor"]
    available = check_sensor(sensor["active"], sensor["battery"])
    temperature = None
    humidity = None
    leak_detected = None
    temperature_normal = False
    humidity_normal = False
    if available:
        # Округляем до анализа, как в ПР1.
        temperature = analyze_metric(
            round(random.uniform(16.0, 28.0), 2), *TEMPERATURE_LIMITS,
        )
        humidity = analyze_metric(
            round(random.uniform(30.0, 75.0), 2), *HUMIDITY_LIMITS,
        )
        leak_detected = random.randint(1, 10) == 1
        temperature_normal = temperature["normal"]
        humidity_normal = humidity["normal"]
    status = get_room_status(
        available, temperature_normal, humidity_normal,
        leak_detected is True,
    )
    return {
        "id": f"REP-{uuid4().hex}",
        "room_id": room["id"],
        "room_name": room["name"],
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "sensor_active": sensor["active"],
        "battery": sensor["battery"],
        "temperature": temperature,
        "humidity": humidity,
        "leak_detected": leak_detected,
        "status": status,
    }
