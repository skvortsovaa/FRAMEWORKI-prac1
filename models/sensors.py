"""Датчик хранит ссылку на объект помещения."""

from dataclasses import dataclass

from models.rooms import Room, get_room
from models.validation import require_text


@dataclass
class Sensor:
    """Один комбинированный датчик на помещение."""

    id: str
    room: Room
    active: bool
    battery: int

    def __init__(self, sensor_id: str, room: Room, active: bool = True,
                 battery: int = 100) -> None:
        self.id = sensor_id
        self.room = room
        self.active = active
        self.battery = battery
        self.validate()

    def validate(self) -> None:
        require_text(self.id, "ID датчика")
        if not isinstance(self.room, Room):
            raise ValueError("Датчик должен ссылаться на объект Room.")
        self.room.validate()
        self._validate_state(self.active, self.battery)

    @staticmethod
    def _validate_state(active: bool, battery: int) -> None:
        if type(active) is not bool:
            raise ValueError("Активность датчика должна быть True или False.")
        if type(battery) is not int or not 0 <= battery <= 100:
            raise ValueError("Заряд должен быть целым числом от 0 до 100.")

    def update_state(self, active: bool, battery: int) -> None:
        """При ошибке оба прежних значения остаются неизменными."""
        self._validate_state(active, battery)
        self.active = active
        self.battery = battery

    def is_available(self) -> bool:
        return self.active and self.battery > 0

    def __str__(self) -> str:
        state = "активен" if self.active else "неактивен"
        return (f"{self.id} | {self.room.name} | {state} | "
                f"заряд {self.battery}%")


def add_sensor(sensors: list[Sensor], rooms: list[Room],
               room_id: int) -> Sensor:
    room = get_room(rooms, room_id)
    if any(sensor.room.id == room_id for sensor in sensors):
        raise ValueError("У помещения уже есть датчик.")
    number = 1
    used = {sensor.id for sensor in sensors}
    while f"SENS-{number:03d}" in used:
        number += 1
    sensor = Sensor(f"SENS-{number:03d}", room)
    sensors.append(sensor)
    return sensor


def get_room_sensor(sensors: list[Sensor], room_id: int) -> Sensor:
    for sensor in sensors:
        if sensor.room.id == room_id:
            return sensor
    raise ValueError(f"Датчик помещения {room_id} не найден.")
