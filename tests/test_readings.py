"""Проверки измерений и сохранения исторической нормы."""

import pytest

from models.metrics import default_metrics, get_metric
from models import Room, Sensor
from models.readings import add_reading, find_readings


SENSOR = Sensor("SENS-001", Room(1, "Архив", 1, 20), True, 85)


def test_reading_keeps_original_limits():
    metric = default_metrics()[0]
    reading = add_reading([], SENSOR, metric, 25, "REP-1", "2026-09-28")
    metric.update_limits(10, 30)
    assert reading.maximum == 24
    assert reading.status == "ПРЕДУПРЕЖДЕНИЕ"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_invalid_value_not_added(value):
    readings = []
    with pytest.raises(ValueError):
        add_reading(readings, SENSOR, default_metrics()[0], value,
                    "REP-1", "2026-09-28")
    assert readings == []


def test_leak_reading_is_emergency():
    metric = get_metric(default_metrics(), "leak")
    reading = add_reading([], SENSOR, metric, 1, "REP-1", "2026-09-28")
    assert reading.status == "АВАРИЯ"
    with pytest.raises(ValueError):
        add_reading([], SENSOR, metric, 2, "REP-1", "2026-09-28")


def test_readings_filtered_and_sorted():
    readings = []
    metric = default_metrics()[0]
    old = add_reading(readings, SENSOR, metric, 20, "REP-1", "2026-09-27")
    new = add_reading(readings, SENSOR, metric, 21, "REP-2", "2026-09-28")
    add_reading(readings, Sensor("SENS-002", SENSOR.room), metric, 22,
                "REP-3", "2026-09-28")
    assert find_readings(readings, SENSOR.id) == [new, old]
