"""Помещение и операции над коллекцией помещений."""

from dataclasses import dataclass
from typing import Iterator

from models.validation import require_number, require_text


@dataclass
class Room:
    """Помещение; конструктор не допускает некорректных полей."""

    id: int
    name: str
    floor: int
    area: float

    def __init__(self, room_id: int, name: str, floor: int,
                 area: float) -> None:
        self.id = room_id
        self.name = name
        self.floor = floor
        self.area = area
        self.validate()
        self.name = name.strip()

    def validate(self) -> None:
        if type(self.id) is not int or self.id <= 0:
            raise ValueError("ID помещения должен быть положительным целым.")
        require_text(self.name, "название помещения")
        if type(self.floor) is not int:
            raise ValueError("Этаж должен быть целым числом.")
        require_number(self.area, "площадь")
        if self.area <= 0:
            raise ValueError("Площадь должна быть больше нуля.")

    def is_on_floor(self, floor: int) -> bool:
        return self.floor == floor

    def __str__(self) -> str:
        return (f"{self.id}. {self.name} | этаж {self.floor} | "
                f"{self.area} кв.м")


def add_room(rooms: list[Room], name: str, floor: int, area: float) -> Room:
    """Создать объект, добавить в коллекцию и вернуть его."""
    room_id = max((room.id for room in rooms), default=0) + 1
    room = Room(room_id, name, floor, area)
    rooms.append(room)
    return room


def get_room(rooms: list[Room], room_id: int) -> Room:
    for room in rooms:
        if room.id == room_id:
            return room
    raise ValueError(f"Помещение с ID {room_id} не найдено.")


def find_rooms(rooms: list[Room], query: str) -> list[Room]:
    return [room for room in rooms
            if query.strip().casefold() in room.name.casefold()]


def sort_rooms(rooms: list[Room]) -> list[Room]:
    """Вернуть новый список, не переставляя исходную коллекцию."""
    return sorted(rooms, key=lambda room: room.area)


def iter_rooms_on_floor(rooms: list[Room], floor: int) -> Iterator[Room]:
    for room in rooms:
        if room.is_on_floor(floor):
            yield room
