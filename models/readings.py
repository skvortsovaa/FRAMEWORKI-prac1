"""Измерение связывает объекты датчика и показателя."""

from dataclasses import dataclass
from uuid import uuid4

from models.metrics import Metric, analyze_metric, get_metric
from models.reports import Report
from models.sensors import Sensor
from models.validation import require_datetime, require_text


@dataclass
class Reading:
    """Значение оценивается по снимку норм, а не по текущему Metric."""

    id: str
    sensor: Sensor
    metric: Metric
    value: float
    report_id: str
    measured_at: str
    minimum: float
    maximum: float
    status: str

    def __init__(self, reading_id: str, sensor: Sensor, metric: Metric,
                 value: float, report_id: str, measured_at: str,
                 minimum: float, maximum: float,
                 status: str | None = None) -> None:
        self.id = reading_id
        self.sensor = sensor
        self.metric = metric
        self.value = value
        self.report_id = report_id
        self.measured_at = measured_at
        self.minimum = minimum
        self.maximum = maximum
        if not isinstance(sensor, Sensor) or not isinstance(metric, Metric):
            raise ValueError("Измерение требует объекты Sensor и Metric.")
        self.status = self.get_status() if status is None else status
        self.validate()

    def get_status(self) -> str:
        result = analyze_metric(self.value, self.minimum, self.maximum)
        if self.metric.id == "leak":
            if self.value not in (0, 1):
                raise ValueError("Значение протечки должно быть 0 или 1.")
            if self.minimum != 0 or self.maximum != 0:
                raise ValueError("Норма протечки должна быть 0.")
            return "АВАРИЯ" if self.value else "НОРМА"
        return "НОРМА" if result.normal else "ПРЕДУПРЕЖДЕНИЕ"

    def validate(self) -> None:
        require_text(self.id, "ID измерения")
        require_text(self.report_id, "ID отчёта измерения")
        require_datetime(self.measured_at)
        if (not isinstance(self.sensor, Sensor)
                or not isinstance(self.metric, Metric)):
            raise ValueError("Измерение требует объекты Sensor и Metric.")
        self.sensor.validate()
        self.metric.validate()
        if self.status != self.get_status():
            raise ValueError("Статус измерения не соответствует значению.")

    def __str__(self) -> str:
        return (f"{self.measured_at} | {self.sensor.id} | "
                f"{self.metric.name}: {self.value} {self.metric.unit} | "
                f"норма {self.minimum}–{self.maximum} | {self.status}")


def add_reading(readings: list[Reading], sensor: Sensor, metric: Metric,
                value: float, report_id: str, measured_at: str) -> Reading:
    reading = Reading(f"READ-{uuid4().hex}", sensor, metric, value,
                      report_id, measured_at, metric.minimum, metric.maximum)
    readings.append(reading)
    return reading


def find_readings(readings: list[Reading], sensor_id: str) -> list[Reading]:
    return sorted((item for item in readings if item.sensor.id == sensor_id),
                  key=lambda item: item.measured_at, reverse=True)


def record_report_readings(readings: list[Reading], sensor: Sensor,
                           metrics: list[Metric], report: Report) -> None:
    """Сохранить исторические нормы и ссылки на текущие объекты."""
    report.validate()
    if sensor.room is not report.room:
        raise ValueError("Датчик и отчёт относятся к разным комнатам.")
    pending = []
    for metric_id in ("temperature", "humidity", "leak"):
        metric = get_metric(metrics, metric_id)
        if metric_id == "leak":
            if report.leak_detected is None:
                continue
            value = int(report.leak_detected)
            minimum, maximum = 0.0, 0.0
        else:
            result = getattr(report, metric_id)
            if result is None:
                continue
            value = result.value
            minimum, maximum = result.minimum, result.maximum
        pending.append(Reading(f"READ-{uuid4().hex}", sensor, metric, value,
                               report.id, report.checked_at, minimum, maximum))
    readings.extend(pending)
