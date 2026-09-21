"""Хранение и обработка помещений и их датчиков."""

from math import isfinite
from typing import Iterator


def validate_room(room: dict) -> None:
    """Проверить поля помещения, в том числе после чтения JSON."""
    if not isinstance(room, dict):
        raise ValueError("Помещение должно быть словарём.")
    if type(room.get("id")) is not int or room["id"] <= 0:
        raise ValueError("ID помещения должен быть положительным целым.")
    name = room.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Название помещения не должно быть пустым.")
    if type(room.get("floor")) is not int:
        raise ValueError("Этаж должен быть целым числом.")
    area = room.get("area")
    if type(area) not in (int, float) or not isfinite(area) or area <= 0:
        raise ValueError("Площадь должна быть конечным числом больше нуля.")
    sensor = room.get("sensor")
    if not isinstance(sensor, dict):
        raise ValueError("У помещения должен быть датчик.")
    if not isinstance(sensor.get("id"), str) or not sensor["id"].strip():
        raise ValueError("ID датчика не должен быть пустым.")
    if type(sensor.get("active")) is not bool:
        raise ValueError("Активность датчика должна быть True или False.")
    battery = sensor.get("battery")
    if type(battery) is not int or not 0 <= battery <= 100:
        raise ValueError("Заряд батареи должен быть целым числом от 0 до 100.")


def add_room(
    rooms: list[dict], name: str, floor: int, area: float,
) -> dict:
    """Добавить помещение с уникальным ID и активным датчиком."""
    room_id = max((room["id"] for room in rooms), default=0) + 1
    room = {
        "id": room_id,
        "name": name.strip(),
        "floor": floor,
        "area": area,
        "sensor": {
            "id": f"SENS-{room_id:03d}",
            "active": True,
            "battery": 100,
        },
    }
    validate_room(room)
    rooms.append(room)
    return room


def get_room(rooms: list[dict], room_id: int) -> dict:
    """Найти помещение по ID или сообщить об ошибке."""
    for room in rooms:
        if room["id"] == room_id:
            return room
    raise ValueError(f"Помещение с ID {room_id} не найдено.")


def find_rooms(rooms: list[dict], query: str) -> list[dict]:
    """Найти помещения по части названия без учёта регистра."""
    return [
        room for room in rooms
        if query.strip().casefold() in room["name"].casefold()
    ]


def sort_rooms(rooms: list[dict]) -> list[dict]:
    """Вернуть новый список помещений по возрастанию площади."""
    return sorted(rooms, key=lambda room: room["area"])


def iter_rooms_on_floor(rooms: list[dict], floor: int) -> Iterator[dict]:
    """По одному выдавать помещения указанного этажа."""
    for room in rooms:
        if room["floor"] == floor:
            yield room


def update_sensor(room: dict, active: bool, battery: int) -> None:
    """Изменить состояние датчика только после проверки новых данных."""
    sensor = {**room["sensor"], "active": active, "battery": battery}
    validate_room({**room, "sensor": sensor})
    room["sensor"] = sensor
