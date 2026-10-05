"""Контракты классов: создание, методы, представление и ссылки."""

from copy import deepcopy

import pytest

from models import Metric, Reading, Room, Sensor
from models.readings import add_reading


def test_objects_and_string_representation():
    room = Room(7, " Архив ", 2, 40)
    sensor = Sensor("S-7", room, True, 85)
    metric = Metric("temperature", "Температура", "°C", 18, 24)
    reading = add_reading([], sensor, metric, 25, "REP-7", "2026-09-28")
    assert (room.id, room.name, room.floor, room.area) == (7, "Архив", 2, 40)
    assert sensor.room is room
    assert reading.sensor is sensor
    assert reading.metric is metric
    assert reading.sensor.room is room
    assert room.is_on_floor(2) and not room.is_on_floor(3)
    assert sensor.is_available()
    assert metric.analyze(24).normal
    assert reading.get_status() == "ПРЕДУПРЕЖДЕНИЕ"
    for item, fragments in [
        (room, ("Архив", "этаж 2", "40")),
        (sensor, ("S-7", "Архив", "85%")),
        (metric, ("Температура", "18", "24", "°C")),
        (reading, ("S-7", "25", "ПРЕДУПРЕЖДЕНИЕ", "2026-09-28")),
    ]:
        assert all(fragment in str(item) for fragment in fragments)
    sensor.update_state(False, 0)
    assert not sensor.is_available()
    metric.update_limits(10, 30)
    assert reading.maximum == 24
    assert reading.get_status() == "ПРЕДУПРЕЖДЕНИЕ"


@pytest.mark.parametrize("args", [
    (True, "Архив", 1, 20), (0, "Архив", 1, 20),
    (1, " ", 1, 20), (1, None, 1, 20),
    (1, "Архив", True, 20), (1, "Архив", 1, True),
])
def test_room_constructor_rejects_invalid_fields(args):
    with pytest.raises(ValueError):
        Room(*args)


@pytest.mark.parametrize("args", [
    ("", "Температура", "°C", 18, 24),
    ("temperature", "", "°C", 18, 24),
    ("temperature", "Температура", "", 18, 24),
    ("temperature", "Температура", "°C", 30, 20),
    ("leak", "Протечка", "0/1", 0, 1),
])
def test_metric_constructor_rejects_invalid_fields(args):
    with pytest.raises(ValueError):
        Metric(*args)


def test_sensor_constructor_requires_room_object():
    with pytest.raises(ValueError):
        Sensor("S-1", 1)


@pytest.mark.parametrize("field,value", [
    ("reading_id", ""), ("sensor", "S-1"), ("metric", "temperature"),
    ("measured_at", "not-a-date"), ("report_id", ""),
    ("status", "UNKNOWN"), ("value", float("nan")),
])
def test_reading_constructor_rejects_invalid_fields(field, value):
    args = {
        "reading_id": "R-1", "sensor": Sensor("S-1", Room(1, "А", 1, 20)),
        "metric": Metric("temperature", "Температура", "°C", 18, 24),
        "value": 21, "report_id": "REP-1", "measured_at": "2026-09-28",
        "minimum": 18, "maximum": 24,
    }
    args[field] = value
    with pytest.raises(ValueError):
        Reading(**args)


def test_deepcopy_keeps_shared_links_inside_copy():
    room = Room(1, "Архив", 1, 20)
    sensor = Sensor("S-1", room)
    metric = Metric("temperature", "Температура", "°C", 18, 24)
    reading = add_reading([], sensor, metric, 21, "REP-1", "2026-09-28")
    copied = deepcopy([room, sensor, metric, reading])
    assert copied[1].room is copied[0]
    assert copied[3].sensor is copied[1]
    assert copied[3].metric is copied[2]
    assert copied[0] is not room
    copied[1].update_state(False, 0)
    assert sensor.is_available()
