"""Файлы, миграция, связи и восстановление после ошибок записи."""

from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from monitoring import check_room
from models.rooms import add_room
from models.sensors import add_sensor
from storage import (
    COLLECTIONS, empty_data, load_data, save_data, validate_data,
)


@pytest.fixture
def data():
    state = empty_data()
    room = add_room(state["rooms"], "Серверная №1", 3, 25.5)
    sensor = add_sensor(state["sensors"], state["rooms"], room["id"])
    with patch("monitoring.random.uniform", side_effect=[21, 50]):
        with patch("monitoring.random.randint", return_value=2):
            report = check_room(room, sensor, state["metrics"],
                                state["readings"])
    state["reports"].append(report)
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
    room = deepcopy(data["rooms"][0])
    sensor = deepcopy(data["sensors"][0])
    sensor.pop("room_id")
    room["sensor"] = sensor
    legacy = {"rooms": [room], "reports": data["reports"]}
    filename = tmp_path / "state.json"
    filename.write_text(json.dumps(legacy, ensure_ascii=False),
                        encoding="utf-8")
    before = filename.read_bytes()
    migrated = load_data(tmp_path)
    assert migrated["rooms"] == data["rooms"]
    assert migrated["sensors"] == data["sensors"]
    assert migrated["reports"] == data["reports"]
    assert len(migrated["readings"]) == 3
    assert migrated["readings"][0]["value"] == 21
    save_data(tmp_path, migrated)
    assert load_data(tmp_path) == migrated
    assert filename.read_bytes() == before


@pytest.mark.parametrize("collection", COLLECTIONS)
def test_duplicate_ids_rejected(data, collection):
    data[collection].append(deepcopy(data[collection][0]))
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
    data[collection][0][field] = value
    with pytest.raises(ValueError):
        validate_data(data)


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
    changed["rooms"][0]["name"] = "Изменено"
    changed["sensors"][0]["battery"] = 42
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
    changed["rooms"][0]["name"] = "Изменено"
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
