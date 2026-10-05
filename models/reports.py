"""Отчёт проверки хранит историческое состояние помещения и датчика."""

from dataclasses import dataclass

from models.metrics import MetricAnalysis
from models.rooms import Room
from models.validation import require_datetime, require_text


def get_room_status(available: bool, temperature_normal: bool,
                    humidity_normal: bool, leak_detected: bool) -> str:
    """Приоритеты статусов сохраняются из ПР1."""
    if not available:
        return "НЕТ ДАННЫХ"
    if leak_detected:
        return "АВАРИЯ"
    if not temperature_normal or not humidity_normal:
        return "ПРЕДУПРЕЖДЕНИЕ"
    return "НОРМА"


@dataclass
class Report:
    """Ссылка на Room и независимые снимки полей на момент проверки."""

    id: str
    room: Room
    room_name: str
    checked_at: str
    sensor_active: bool
    battery: int
    temperature: MetricAnalysis | None
    humidity: MetricAnalysis | None
    leak_detected: bool | None
    status: str

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        require_text(self.id, "ID отчёта")
        require_text(self.room_name, "название помещения в отчёте")
        require_datetime(self.checked_at)
        if not isinstance(self.room, Room):
            raise ValueError("Отчёт должен ссылаться на объект Room.")
        if type(self.sensor_active) is not bool:
            raise ValueError("Некорректная активность датчика в отчёте.")
        if type(self.battery) is not int or not 0 <= self.battery <= 100:
            raise ValueError("Некорректный заряд датчика в отчёте.")
        available = self.sensor_active and self.battery > 0
        if available:
            if (not isinstance(self.temperature, MetricAnalysis)
                    or not isinstance(self.humidity, MetricAnalysis)
                    or type(self.leak_detected) is not bool):
                raise ValueError("В отчёте отсутствуют корректные показания.")
            expected = get_room_status(True, self.temperature.normal,
                                       self.humidity.normal,
                                       self.leak_detected)
        else:
            if any(value is not None for value in
                   (self.temperature, self.humidity, self.leak_detected)):
                raise ValueError("Недоступный датчик не имеет показаний.")
            expected = "НЕТ ДАННЫХ"
        if self.status != expected:
            raise ValueError("Статус отчёта не соответствует показаниям.")

    def __str__(self) -> str:
        return (f"{self.checked_at} | {self.room_name} | "
                f"{self.status} | {self.id}")
