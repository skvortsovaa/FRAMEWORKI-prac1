"""Сущность «Датчик»: один комбинированный датчик на помещение."""

from models.rooms import get_room


def validate_sensor(sensor: dict) -> None:
    """Проверить поля датчика независимо от файлов и меню."""
    if not isinstance(sensor, dict):
        raise ValueError("Датчик должен быть словарём.")
    if not isinstance(sensor.get("id"), str) or not sensor["id"].strip():
        raise ValueError("ID датчика не должен быть пустым.")
    if type(sensor.get("room_id")) is not int or sensor["room_id"] <= 0:
        raise ValueError("ID помещения датчика должен быть положительным.")
    if type(sensor.get("active")) is not bool:
        raise ValueError("Активность датчика должна быть True или False.")
    battery = sensor.get("battery")
    if type(battery) is not int or not 0 <= battery <= 100:
        raise ValueError("Заряд батареи должен быть целым числом от 0 до 100.")


def add_sensor(sensors: list[dict], rooms: list[dict], room_id: int) -> dict:
    """Создать датчик для существующего помещения без датчика."""
    get_room(rooms, room_id)
    if any(sensor["room_id"] == room_id for sensor in sensors):
        raise ValueError("У помещения уже есть датчик.")
    number = 1
    used = {sensor["id"] for sensor in sensors}
    while f"SENS-{number:03d}" in used:
        number += 1
    sensor = {
        "id": f"SENS-{number:03d}", "room_id": room_id,
        "active": True, "battery": 100,
    }
    validate_sensor(sensor)
    sensors.append(sensor)
    return sensor


def get_room_sensor(sensors: list[dict], room_id: int) -> dict:
    """Найти датчик помещения по внешнему ключу room_id."""
    for sensor in sensors:
        if sensor["room_id"] == room_id:
            return sensor
    raise ValueError(f"Датчик помещения {room_id} не найден.")


def update_sensor(sensor: dict, active: bool, battery: int) -> None:
    """Применить изменения только после проверки всех новых значений."""
    candidate = {**sensor, "active": active, "battery": battery}
    validate_sensor(candidate)
    sensor.update(candidate)
