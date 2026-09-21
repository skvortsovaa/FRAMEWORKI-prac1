"""Проверки коллекции помещений."""

import pytest

from rooms import (
    add_room, find_rooms, get_room, iter_rooms_on_floor,
    sort_rooms, update_sensor,
)


def test_add_room():
    rooms = []
    add_room(rooms, "Серверная", 3, 25.5)
    assert rooms[0]["name"] == "Серверная"
    assert rooms[0]["sensor"]["active"] is True


def test_find_rooms_ignores_case():
    rooms = []
    room = add_room(rooms, "Серверная", 3, 25.5)
    assert find_rooms(rooms, "СЕРВ") == [room]


def test_sort_rooms_does_not_change_original():
    rooms = []
    large = add_room(rooms, "Архив", 2, 40.0)
    small = add_room(rooms, "Серверная", 3, 25.5)
    assert sort_rooms(rooms) == [small, large]
    assert rooms == [large, small]


def test_filter_rooms_by_floor():
    rooms = []
    selected = add_room(rooms, "Серверная", 3, 25.5)
    add_room(rooms, "Архив", 2, 40.0)
    assert list(iter_rooms_on_floor(rooms, 3)) == [selected]


def test_unknown_room():
    with pytest.raises(ValueError, match="не найдено"):
        get_room([], 99)


@pytest.mark.parametrize("battery", [-1, 101, True])
def test_invalid_sensor_update_keeps_old_values(battery):
    room = add_room([], "Серверная", 3, 25.5)
    with pytest.raises(ValueError):
        update_sensor(room, False, battery)
    assert room["sensor"]["active"] is True
    assert room["sensor"]["battery"] == 100


@pytest.mark.parametrize("area", [0, -1, float("nan"), float("inf")])
def test_invalid_area_does_not_add_room(area):
    rooms = []
    with pytest.raises(ValueError):
        add_room(rooms, "Серверная", 3, area)
    assert rooms == []
