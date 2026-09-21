"""Проверки правил мониторинга, сохранённых из ПР1."""

from unittest.mock import patch

import pytest

from monitoring import analyze_metric, check_room, get_room_status
from rooms import add_room, update_sensor


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
    update_sensor(room, active, battery)
    with patch("monitoring.random.uniform") as uniform:
        with patch("monitoring.random.randint") as randint:
            report = check_room(room)
    uniform.assert_not_called()
    randint.assert_not_called()
    assert report["status"] == "НЕТ ДАННЫХ"
    assert report["temperature"] is None
    assert report["humidity"] is None
    assert report["leak_detected"] is None


def test_low_battery_does_not_change_normal_room_status():
    room = add_room([], "Серверная", 3, 25.5)
    update_sensor(room, True, 15)
    with patch("monitoring.random.uniform", side_effect=[21, 50]):
        with patch("monitoring.random.randint", return_value=2):
            report = check_room(room)
    assert report["status"] == "НОРМА"
    assert report["battery"] == 15
