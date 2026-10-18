"""Чтение JSON на страницах помещений без изменения хранилища ПР3."""

import json
import os
from unittest.mock import patch

import django
from django.test import Client, override_settings
from django.utils.html import escape
import pytest

from models import Room, Sensor
from storage import COLLECTIONS, JOURNAL, empty_data, save_data


@pytest.fixture
def web_client(tmp_path):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartspace_web.settings")
    django.setup()
    with override_settings(BASE_DIR=tmp_path, ALLOWED_HOSTS=["testserver"],
                           DEBUG=True):
        yield Client()


@pytest.fixture
def project_data():
    data = empty_data()
    server = Room(7, "Серверная №7", 3, 25.5)
    archive = Room(12, "Архив №12", 8, 42.5)
    data.rooms.extend([server, archive])
    # Порядок датчиков отличается от порядка помещений: важна связь по ID.
    data.sensors.extend([
        Sensor("SENS-ARCHIVE", archive, True, 73),
        Sensor("SENS-SERVER", server),
    ])
    return data


@pytest.fixture
def saved_data(tmp_path, project_data):
    directory = tmp_path / "data"
    save_data(directory, project_data)
    return directory


def snapshot(directory):
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*") if path.is_file()
    }


def test_web_loader_restores_objects_and_shared_links(web_client, saved_data):
    from smartspace_web.data import load_project_data

    before = snapshot(saved_data)
    data = load_project_data()

    assert isinstance(data.rooms[0], Room)
    assert isinstance(data.sensors[0], Sensor)
    assert data.rooms[0].id == 7
    assert data.sensors[0].room is data.rooms[1]
    assert data.sensors[1].room is data.rooms[0]
    assert {metric.id for metric in data.metrics} == {
        "temperature", "humidity", "leak",
    }
    assert snapshot(saved_data) == before


def test_room_list_displays_saved_rooms(web_client, saved_data):
    before = snapshot(saved_data)
    response = web_client.get("/rooms/")
    body = response.content.decode()

    assert response.status_code == 200
    for text in ("Серверная №7", "Архив №12", "/rooms/7/", "/rooms/12/"):
        assert text in body
    assert "25.5" in body or "25,5" in body
    assert "42.5" in body or "42,5" in body
    assert snapshot(saved_data) == before


def test_room_detail_displays_linked_sensor(web_client, saved_data):
    before = snapshot(saved_data)
    response = web_client.get("/rooms/12/")
    body = response.content.decode()

    assert response.status_code == 200
    for text in ("Архив №12", "SENS-ARCHIVE", "73", "8", "/rooms/"):
        assert text in body
    assert "42.5" in body or "42,5" in body
    assert "SENS-SERVER" not in body
    assert "Серверная №7" not in body
    assert snapshot(saved_data) == before


@pytest.mark.parametrize("active,battery,status", [
    (True, 100, "Доступен"),
    (False, 100, "Недоступен"),
    (True, 0, "Недоступен"),
])
def test_sensor_availability(web_client, saved_data, project_data,
                             active, battery, status):
    project_data.sensors[1].update_state(active, battery)
    save_data(saved_data, project_data)
    before = snapshot(saved_data)

    response = web_client.get("/rooms/7/")

    assert response.status_code == 200
    assert status in response.content.decode()
    assert snapshot(saved_data) == before


def test_detail_uses_sensor_availability_method(web_client, saved_data):
    with patch.object(Sensor, "is_available", autospec=True,
                      return_value=False) as availability:
        response = web_client.get("/rooms/7/")

    assert response.status_code == 200
    assert "Недоступен" in response.content.decode()
    availability.assert_called_once()
    assert availability.call_args.args[0].id == "SENS-SERVER"


def test_unknown_room_has_formatted_404_in_debug_mode(web_client, saved_data):
    before = snapshot(saved_data)
    response = web_client.get("/rooms/999/")
    body = response.content.decode()

    assert response.status_code == 404
    assert "Помещение не найдено" in body
    assert "SmartSpace Monitor" in body
    assert 'href="/rooms/"' in body
    assert "Traceback" not in body
    assert snapshot(saved_data) == before


def test_empty_collection_is_a_successful_page(web_client, tmp_path):
    directory = tmp_path / "data"
    save_data(directory, empty_data())
    before = snapshot(directory)

    response = web_client.get("/rooms/")

    assert response.status_code == 200
    assert "Помещения пока не добавлены" in response.content.decode()
    assert snapshot(directory) == before


def test_saved_names_and_sensor_ids_are_escaped(
        web_client, saved_data, project_data):
    room_name = '<script>alert("room")</script> & серверная'
    sensor_id = '<img src=x onerror="alert(1)"> & датчик'
    project_data.rooms[0].name = room_name
    project_data.sensors[1].id = sensor_id
    save_data(saved_data, project_data)
    before = snapshot(saved_data)

    for url in ("/rooms/", "/rooms/7/"):
        response = web_client.get(url)
        body = response.content.decode()
        assert response.status_code == 200
        assert room_name not in body
        assert str(escape(room_name)) in body
        assert sensor_id not in body
        if url == "/rooms/7/":
            assert str(escape(sensor_id)) in body
    assert snapshot(saved_data) == before


@pytest.mark.parametrize("problem", [
    "broken_json", "broken_link", "invalid_metrics", "journal", "huge_area",
    *[f"missing_{name}" for name in COLLECTIONS],
])
def test_storage_errors_are_safe_and_do_not_modify_files(
        web_client, saved_data, problem):
    if problem == "broken_json":
        (saved_data / "rooms.json").write_text('{"broken":',
                                               encoding="utf-8")
    elif problem == "broken_link":
        path = saved_data / "sensors.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw[0]["room_id"] = 999
        path.write_text(json.dumps(raw), encoding="utf-8")
    elif problem == "invalid_metrics":
        (saved_data / "metrics.json").write_text("[]", encoding="utf-8")
    elif problem == "huge_area":
        path = saved_data / "rooms.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw[0]["area"] = 10 ** 400
        path.write_text(json.dumps(raw), encoding="utf-8")
    elif problem == "journal":
        # Такой журнал действительно изменил бы данные при recover_save().
        backup = {f"{name}.json": "[]\n" for name in COLLECTIONS}
        journal = saved_data / JOURNAL
        journal.write_text(json.dumps(backup), encoding="utf-8")
    else:
        collection = problem.removeprefix("missing_")
        (saved_data / f"{collection}.json").unlink()
    before = snapshot(saved_data)

    for url in ("/rooms/", "/rooms/7/"):
        response = web_client.get(url)
        body = response.content.decode()
        assert response.status_code == 503
        assert "SmartSpace Monitor" in body
        assert "Traceback" not in body
        assert str(saved_data) not in body
        assert saved_data.as_posix() not in body
        assert snapshot(saved_data) == before


def test_missing_storage_is_not_created(web_client, tmp_path):
    directory = tmp_path / "data"
    assert not directory.exists()

    response = web_client.get("/rooms/")

    assert response.status_code == 503
    assert not directory.exists()
