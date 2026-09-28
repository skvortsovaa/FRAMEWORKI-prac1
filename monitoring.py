"""Исходный сценарий ПР1: измерения и оценка состояния помещения."""

from datetime import datetime
import random
from uuid import uuid4

from models.metrics import analyze_metric, get_metric
from models.readings import record_report_readings
from models.rooms import validate_room
from models.sensors import validate_sensor


def check_sensor(active: bool, battery: int) -> bool:
    """Доступны ли измерения: датчик включён и батарея не разряжена."""
    return active and battery > 0


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


def check_room(
    room: dict, sensor: dict, metrics: list[dict], readings: list[dict],
) -> dict:
    """Выполнить одну учебную проверку и вернуть запись для истории."""
    validate_room(room)
    validate_sensor(sensor)
    if sensor["room_id"] != room["id"]:
        raise ValueError("Датчик принадлежит другому помещению.")
    temperature_metric = get_metric(metrics, "temperature")
    humidity_metric = get_metric(metrics, "humidity")
    available = check_sensor(sensor["active"], sensor["battery"])
    temperature = None
    humidity = None
    leak_detected = None
    temperature_normal = False
    humidity_normal = False
    if available:
        # Округляем до анализа, как в ПР1.
        temperature = analyze_metric(
            round(random.uniform(16.0, 28.0), 2),
            temperature_metric["minimum"], temperature_metric["maximum"],
        )
        humidity = analyze_metric(
            round(random.uniform(30.0, 75.0), 2),
            humidity_metric["minimum"], humidity_metric["maximum"],
        )
        leak_detected = random.randint(1, 10) == 1
        temperature_normal = temperature["normal"]
        humidity_normal = humidity["normal"]
    status = get_room_status(
        available, temperature_normal, humidity_normal,
        leak_detected is True,
    )
    report = {
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
    record_report_readings(readings, sensor, metrics, report)
    return report
