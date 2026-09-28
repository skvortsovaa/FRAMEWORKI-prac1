"""Сущность «Измерение»: значение, датчик, показатель и время."""

from datetime import datetime
from uuid import uuid4

from models.metrics import analyze_metric, get_metric, validate_metric
from models.sensors import validate_sensor


def validate_reading(reading: dict) -> None:
    """Проверить измерение вместе со снимком нормы на момент проверки."""
    if not isinstance(reading, dict):
        raise ValueError("Измерение должно быть словарём.")
    for field in ("id", "sensor_id", "metric_id", "report_id", "measured_at"):
        value = reading.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Некорректное поле измерения: {field}.")
    try:
        datetime.fromisoformat(reading["measured_at"])
    except ValueError as error:
        raise ValueError("Некорректное время измерения.") from error
    result = analyze_metric(
        reading.get("value"), reading.get("minimum"), reading.get("maximum"),
    )
    status = "НОРМА" if result["normal"] else "ПРЕДУПРЕЖДЕНИЕ"
    if reading["metric_id"] == "leak":
        if reading["value"] not in (0, 1):
            raise ValueError("Значение протечки должно быть 0 или 1.")
        if reading["minimum"] != 0 or reading["maximum"] != 0:
            raise ValueError("Норма протечки должна быть 0.")
        status = "АВАРИЯ" if reading["value"] else "НОРМА"
    if reading.get("status") != status:
        raise ValueError("Статус измерения не соответствует значению.")


def add_reading(
    readings: list[dict], sensor: dict, metric: dict, value: float,
    report_id: str, measured_at: str,
) -> dict:
    """Добавить измерение со связями и независимым снимком границ нормы."""
    validate_sensor(sensor)
    validate_metric(metric)
    result = analyze_metric(value, metric["minimum"], metric["maximum"])
    status = "НОРМА" if result["normal"] else "ПРЕДУПРЕЖДЕНИЕ"
    if metric["id"] == "leak" and value == 1:
        status = "АВАРИЯ"
    reading = {
        "id": f"READ-{uuid4().hex}", "sensor_id": sensor["id"],
        "metric_id": metric["id"], "report_id": report_id,
        "measured_at": measured_at, "value": value,
        "minimum": metric["minimum"], "maximum": metric["maximum"],
        "status": status,
    }
    validate_reading(reading)
    readings.append(reading)
    return reading


def find_readings(readings: list[dict], sensor_id: str) -> list[dict]:
    """Вернуть измерения выбранного датчика от новых к старым."""
    return sorted(
        (item for item in readings if item["sensor_id"] == sensor_id),
        key=lambda item: item["measured_at"], reverse=True,
    )


def record_report_readings(
    readings: list[dict], sensor: dict, metrics: list[dict], report: dict,
) -> None:
    """Выделить измерения из отчёта, включая отчёты старого формата."""
    pending = []
    for metric_id in ("temperature", "humidity", "leak"):
        metric = get_metric(metrics, metric_id)
        if metric_id == "leak":
            value = report.get("leak_detected")
            if value is None:
                continue
            value = int(value)
        else:
            result = report.get(metric_id)
            if result is None:
                continue
            value = result["value"]
            metric = {**metric, "minimum": result["minimum"],
                      "maximum": result["maximum"]}
        add_reading(
            pending, sensor, metric, value, report["id"], report["checked_at"],
        )
    readings.extend(pending)
