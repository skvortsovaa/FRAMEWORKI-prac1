"""Файлы, миграция, связи и восстановление после ошибок записи."""

from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from monitoring import check_room
from models import Metric, Reading, Report, Room, Sensor
from models.rooms import add_room
from models.sensors import add_sensor
from storage import (
    COLLECTIONS, decode_data, empty_data, encode_data, load_data,
    save_data, validate_data,
)


@pytest.fixture
def data():
    state = empty_data()
    room = add_room(state.rooms, "Серверная №1", 3, 25.5)
    sensor = add_sensor(state.sensors, state.rooms, room.id)
    with patch("monitoring.random.uniform", side_effect=[21, 50]):
        with patch("monitoring.random.randint", return_value=2):
            report = check_room(room, sensor, state.metrics,
                                state.readings)
    state.reports.append(report)
    return state


def test_round_trip(tmp_path, data):
    save_data(tmp_path, data)
    assert load_data(tmp_path) == data
    assert all((tmp_path / f"{name}.json").exists() for name in COLLECTIONS)
    assert "Серверная" in (tmp_path / "rooms.json").read_text(encoding="utf-8")


def test_missing_files(tmp_path):
    assert load_data(tmp_path) == empty_data()


@pytest.mark.parametrize("content", [
    '{"rooms":', '[]', '{"rooms": [], "reports": {}}',
])
def test_invalid_legacy_is_not_overwritten(tmp_path, content):
    filename = tmp_path / "state.json"
    filename.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_data(tmp_path)
    assert filename.read_text(encoding="utf-8") == content


def test_legacy_migration_preserves_history_and_source(tmp_path, data):
    raw = encode_data(data)
    room = deepcopy(raw["rooms"][0])
    sensor = deepcopy(raw["sensors"][0])
    sensor.pop("room_id")
    room["sensor"] = sensor
    legacy = {"rooms": [room], "reports": raw["reports"]}
    filename = tmp_path / "state.json"
    filename.write_text(json.dumps(legacy, ensure_ascii=False),
                        encoding="utf-8")
    before = filename.read_bytes()
    migrated = load_data(tmp_path)
    assert migrated.rooms == data.rooms
    assert migrated.sensors == data.sensors
    assert migrated.reports == data.reports
    assert len(migrated.readings) == 3
    assert migrated.readings[0].value == 21
    save_data(tmp_path, migrated)
    assert load_data(tmp_path) == migrated
    assert filename.read_bytes() == before


@pytest.mark.parametrize("collection", COLLECTIONS)
def test_duplicate_ids_rejected(data, collection):
    getattr(data, collection).append(deepcopy(getattr(data, collection)[0]))
    with pytest.raises(ValueError, match="Повторяется"):
        validate_data(data)


@pytest.mark.parametrize("collection,field,value", [
    ("sensors", "room_id", 99),
    ("reports", "room_id", 99),
    ("readings", "sensor_id", "missing"),
    ("readings", "metric_id", "missing"),
    ("readings", "report_id", "missing"),
])
def test_broken_links_rejected(data, collection, field, value):
    raw = encode_data(data)
    raw[collection][0][field] = value
    with pytest.raises(ValueError):
        decode_data(raw)


def test_incomplete_collection_set_rejected(tmp_path):
    (tmp_path / "rooms.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="Неполный"):
        load_data(tmp_path)


def test_corrupt_collection_does_not_fall_back_to_legacy(tmp_path, data):
    save_data(tmp_path, data)
    (tmp_path / "sensors.json").write_text("broken", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON"):
        load_data(tmp_path)


def test_failed_save_rolls_back_all_collections(tmp_path, data):
    save_data(tmp_path, data)
    before = {p.name: p.read_bytes() for p in tmp_path.glob("*.json")}
    changed = deepcopy(data)
    changed.rooms[0].name = "Изменено"
    changed.sensors[0].battery = 42
    original_replace = Path.replace
    failed = False

    def fail_once(path, target):
        nonlocal failed
        if Path(target).name == "sensors.json" and not failed:
            failed = True
            raise OSError("Нет доступа")
        return original_replace(path, target)

    with patch.object(Path, "replace", fail_once):
        with pytest.raises(OSError):
            save_data(tmp_path, changed)
    assert load_data(tmp_path) == data
    assert {p.name: p.read_bytes() for p in tmp_path.glob("*.json")} == before


def test_interrupted_save_recovers_on_next_load(tmp_path, data):
    save_data(tmp_path, data)
    changed = deepcopy(data)
    changed.rooms[0].name = "Изменено"
    original_replace = Path.replace

    def interrupt(path, target):
        if Path(target).name == "sensors.json":
            raise KeyboardInterrupt
        return original_replace(path, target)

    with patch.object(Path, "replace", interrupt):
        with pytest.raises(KeyboardInterrupt):
            save_data(tmp_path, changed)
    assert load_data(tmp_path) == data


def test_failed_first_save_leaves_empty_project(tmp_path, data):
    original_replace = Path.replace

    def fail(path, target):
        if Path(target).name == "sensors.json":
            raise OSError("Нет доступа")
        return original_replace(path, target)

    with patch.object(Path, "replace", fail):
        with pytest.raises(OSError):
            save_data(tmp_path, data)
    assert load_data(tmp_path) == empty_data()


def test_round_trip_restores_types_and_shared_links(tmp_path, data):
    save_data(tmp_path, data)
    restored = load_data(tmp_path)
    assert isinstance(restored.rooms[0], Room)
    assert isinstance(restored.sensors[0], Sensor)
    assert isinstance(restored.metrics[0], Metric)
    assert isinstance(restored.readings[0], Reading)
    assert isinstance(restored.reports[0], Report)
    assert restored.sensors[0].room is restored.rooms[0]
    assert restored.reports[0].room is restored.rooms[0]
    for reading in restored.readings:
        assert reading.sensor is restored.sensors[0]
        assert any(reading.metric is metric for metric in restored.metrics)
    raw = json.loads((tmp_path / "sensors.json").read_text(encoding="utf-8"))
    assert raw[0]["room_id"] == restored.rooms[0].id
    assert "room" not in raw[0]
    assert "Серверная №1" in str(restored.reports[0])


def test_historical_snapshots_survive_updates_and_reload(tmp_path, data):
    data.metrics[0].update_limits(0, 30)
    data.sensors[0].update_state(False, 0)
    data.rooms[0].name = "Новое название"
    save_data(tmp_path, data)
    restored = load_data(tmp_path)
    reading = restored.readings[0]
    report = restored.reports[0]
    assert reading.metric.maximum == 30
    assert reading.maximum == 24
    assert report.temperature.maximum == 24
    assert report.sensor_active is True
    assert report.battery == 100
    assert report.room_name == "Серверная №1"
    assert report.room.name == "Новое название"
    assert not reading.sensor.is_available()


@pytest.mark.parametrize("field,value", [
    ("status", "UNKNOWN"), ("status", "АВАРИЯ"),
    ("checked_at", "not-a-date"), ("checked_at", None),
    ("temperature", None), ("humidity", []),
    ("sensor_active", 1), ("battery", True), ("battery", 101),
    ("leak_detected", "false"),
])
def test_invalid_reports_rejected_without_overwriting(tmp_path, data,
                                                      field, value):
    save_data(tmp_path, data)
    path = tmp_path / "reports.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw[0][field] = value
    path.write_text(json.dumps(raw), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        load_data(tmp_path)
    assert path.read_bytes() == before


@pytest.mark.parametrize("field", ["temperature", "status", "room_id"])
def test_missing_report_fields_rejected(data, field):
    raw = encode_data(data)
    del raw["reports"][0][field]
    with pytest.raises(ValueError):
        decode_data(raw)


def test_inconsistent_analysis_rejected(data):
    raw = encode_data(data)
    raw["reports"][0]["temperature"]["normal"] = False
    with pytest.raises(ValueError):
        decode_data(raw)


@pytest.mark.parametrize("collection,field", [
    ("sensors", "room_id"), ("reports", "room_id"),
    ("readings", "sensor_id"),
])
def test_invalid_link_types_rejected(data, collection, field):
    raw = encode_data(data)
    raw[collection][0][field] = True
    with pytest.raises(ValueError):
        decode_data(raw)


@pytest.mark.parametrize("collection,field", [
    ("sensors", "room"), ("reports", "room"),
    ("readings", "sensor"), ("readings", "metric"),
])
def test_detached_duplicate_objects_rejected(data, collection, field):
    item = getattr(data, collection)[0]
    setattr(item, field, deepcopy(getattr(item, field)))
    with pytest.raises(ValueError):
        validate_data(data)


def test_null_reading_status_rejected(data):
    raw = encode_data(data)
    raw["readings"][0]["status"] = None
    with pytest.raises(ValueError):
        decode_data(raw)


def test_inconsistent_reading_and_report_rejected(data):
    data.readings[0].value = 22
    with pytest.raises(ValueError, match="отчёту"):
        validate_data(data)


def test_unavailable_report_round_trip(tmp_path, data):
    sensor = data.sensors[0]
    sensor.update_state(False, 0)
    report = check_room(data.rooms[0], sensor, data.metrics, data.readings)
    data.reports.append(report)
    save_data(tmp_path, data)
    restored = load_data(tmp_path)
    assert restored.reports[-1].status == "НЕТ ДАННЫХ"
    assert restored.reports[-1].temperature is None
    assert len(restored.readings) == 3
