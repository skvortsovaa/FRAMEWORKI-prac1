"""Проверки правил мониторинга, сохранённых из ПР1."""

from unittest.mock import patch

import pytest

from monitoring import analyze_metric, check_room, get_room_status
from models.metrics import default_metrics, get_metric, update_limits
from models.rooms import add_room
from models.sensors import add_sensor, update_sensor


@pytest.mark.parametrize(
    "value, normal, deviation",
    [(16, False, 2), (18, True, 3), (21, True, 0),
     (24, True, 3), (28, False, 4)],
)
def test_temperature_boundaries(value, normal, deviation):
    result = analyze_metric(value, 18, 24)
    assert result["normal"] is normal
    assert result["deviation"] == deviation


@pytest.mark.parametrize(
    "available, temperature, humidity, leak, expected",
    [(False, False, False, True, "НЕТ ДАННЫХ"),
     (True, False, False, True, "АВАРИЯ"),
     (True, False, True, False, "ПРЕДУПРЕЖДЕНИЕ"),
     (True, True, False, False, "ПРЕДУПРЕЖДЕНИЕ"),
     (True, True, True, False, "НОРМА")],
)
def test_room_status(available, temperature, humidity, leak, expected):
    assert get_room_status(available, temperature, humidity, leak) == expected


@pytest.mark.parametrize("active, battery", [(False, 85), (True, 0)])
def test_unavailable_sensor_does_not_generate_readings(active, battery):
    room = add_room([], "Серверная", 3, 25.5)
    sensor = add_sensor([], [room], room["id"])
    update_sensor(sensor, active, battery)
    readings = []
    with patch("monitoring.random.uniform") as uniform:
        with patch("monitoring.random.randint") as randint:
            report = check_room(room, sensor, default_metrics(), readings)
    assert readings == []
    uniform.assert_not_called()
    randint.assert_not_called()
    assert report["status"] == "НЕТ ДАННЫХ"
    assert report["temperature"] is None
    assert report["humidity"] is None
    assert report["leak_detected"] is None


def test_low_battery_does_not_change_normal_room_status():
    room = add_room([], "Серверная", 3, 25.5)
    sensor = add_sensor([], [room], room["id"])
    update_sensor(sensor, True, 15)
    readings = []
    with patch("monitoring.random.uniform", side_effect=[21, 50]):
        with patch("monitoring.random.randint", return_value=2):
            report = check_room(room, sensor, default_metrics(), readings)
    assert report["status"] == "НОРМА"
    assert report["battery"] == 15


def test_configured_limits_and_reading_links():
    room = add_room([], "Архив", 1, 20)
    sensor = add_sensor([], [room], room["id"])
    metrics = default_metrics()
    update_limits(get_metric(metrics, "temperature"), 10, 20)
    readings = []
    with patch("monitoring.random.uniform", side_effect=[21, 50]):
        with patch("monitoring.random.randint", return_value=2):
            report = check_room(room, sensor, metrics, readings)
    assert report["status"] == "ПРЕДУПРЕЖДЕНИЕ"
    assert len(readings) == 3
    assert {r["metric_id"] for r in readings} == {
        "temperature", "humidity", "leak",
    }
    assert all(r["report_id"] == report["id"] for r in readings)
    assert all(r["sensor_id"] == sensor["id"] for r in readings)
    assert readings[0]["maximum"] == 20
    update_limits(get_metric(metrics, "temperature"), 0, 30)
    assert readings[0]["maximum"] == 20


def test_sensor_from_another_room_is_rejected():
    room = add_room([], "Архив", 1, 20)
    sensor = {"id": "S-2", "room_id": 2, "active": True, "battery": 100}
    with pytest.raises(ValueError, match="другому"):
        check_room(room, sensor, default_metrics(), [])
