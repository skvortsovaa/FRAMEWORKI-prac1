"""Проверки самостоятельной сущности датчика."""

import pytest

from models.rooms import add_room
from models.sensors import add_sensor, get_room_sensor, update_sensor


def test_sensor_links_to_room_and_updates():
    room = add_room([], "Архив", 2, 40)
    sensors = []
    sensor = add_sensor(sensors, [room], room["id"])
    update_sensor(sensor, False, 15)
    assert get_room_sensor(sensors, room["id"]) == sensor
    assert sensor["active"] is False
    assert sensor["battery"] == 15


def test_unknown_room_cannot_have_sensor():
    sensors = []
    with pytest.raises(ValueError):
        add_sensor(sensors, [], 99)
    assert sensors == []


def test_second_sensor_in_room_is_rejected():
    room = add_room([], "Архив", 2, 40)
    sensors = []
    add_sensor(sensors, [room], room["id"])
    with pytest.raises(ValueError, match="уже есть"):
        add_sensor(sensors, [room], room["id"])
    assert len(sensors) == 1


@pytest.mark.parametrize("active,battery", [
    (False, -1), (False, 101), (False, True), (1, 50),
])
def test_invalid_update_keeps_old_values(active, battery):
    room = add_room([], "Архив", 2, 40)
    sensor = add_sensor([], [room], room["id"])
    before = sensor.copy()
    with pytest.raises(ValueError):
        update_sensor(sensor, active, battery)
    assert sensor == before
