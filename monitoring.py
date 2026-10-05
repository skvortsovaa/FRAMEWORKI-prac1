"""Проверка помещения координирует объекты и сохраняет правила ПР1."""

from datetime import datetime
import random
from uuid import uuid4

from models.metrics import Metric, get_metric
from models.readings import Reading, record_report_readings
from models.reports import Report, get_room_status
from models.rooms import Room
from models.sensors import Sensor


def check_room(room: Room, sensor: Sensor, metrics: list[Metric],
               readings: list[Reading]) -> Report:
    """Вернуть отчёт и добавить три измерения доступного датчика."""
    room.validate()
    sensor.validate()
    if sensor.room is not room:
        raise ValueError("Датчик принадлежит другому помещению.")
    temperature_metric = get_metric(metrics, "temperature")
    humidity_metric = get_metric(metrics, "humidity")
    temperature = None
    humidity = None
    leak_detected = None
    available = sensor.is_available()
    if available:
        temperature = temperature_metric.analyze(
            round(random.uniform(16.0, 28.0), 2),
        )
        humidity = humidity_metric.analyze(
            round(random.uniform(30.0, 75.0), 2),
        )
        leak_detected = random.randint(1, 10) == 1
    status = get_room_status(
        available, temperature.normal if temperature else False,
        humidity.normal if humidity else False, leak_detected is True,
    )
    report = Report(f"REP-{uuid4().hex}", room, room.name,
                    datetime.now().isoformat(timespec="seconds"),
                    sensor.active, sensor.battery, temperature, humidity,
                    leak_detected, status)
    record_report_readings(readings, sensor, metrics, report)
    return report
