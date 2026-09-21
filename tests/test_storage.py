"""Проверки JSON на временных файлах, без изменения данных проекта."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from monitoring import check_room
from rooms import add_room, update_sensor
from storage import load_data, save_data


def test_round_trip(tmp_path):
    data = {"rooms": [], "reports": []}
    room = add_room(data["rooms"], "Серверная №1", 3, 25.5)
    update_sensor(room, False, 85)
    data["reports"].append(check_room(room))
    filename = tmp_path / "state.json"
    save_data(filename, data)
    assert load_data(filename) == data
    assert "Серверная" in filename.read_text(encoding="utf-8")


def test_missing_file(tmp_path):
    assert load_data(tmp_path / "missing.json") == {
        "rooms": [], "reports": [],
    }


@pytest.mark.parametrize(
    "content", ['{"rooms":', '[]', '{"rooms": [], "reports": {}}'],
)
def test_invalid_json_is_not_overwritten(tmp_path, content):
    filename = tmp_path / "state.json"
    filename.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_data(filename)
    assert filename.read_text(encoding="utf-8") == content


def test_duplicate_room_ids_are_rejected(tmp_path):
    room = add_room([], "Серверная", 3, 25.5)
    filename = tmp_path / "state.json"
    filename.write_text(json.dumps({
        "rooms": [room, room], "reports": [],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="Повторяется"):
        load_data(filename)


def test_failed_save_preserves_existing_file(tmp_path):
    filename = tmp_path / "state.json"
    data = {"rooms": [], "reports": []}
    save_data(filename, data)
    previous_content = filename.read_bytes()
    add_room(data["rooms"], "Серверная", 3, 25.5)
    with patch.object(Path, "replace", side_effect=OSError("Нет доступа")):
        with pytest.raises(OSError):
            save_data(filename, data)
    assert filename.read_bytes() == previous_content
