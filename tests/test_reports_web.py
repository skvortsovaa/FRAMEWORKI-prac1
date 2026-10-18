"""Исторические снимки отчётов в браузере и чтение без записи."""

from html import escape
import json
import os

import django
from django.test import Client, override_settings
from django.urls import reverse
import pytest

from models import Report, Room, Sensor
from models.metrics import analyze_metric
from storage import COLLECTIONS, JOURNAL, empty_data, save_data


def snapshot(directory):
    return {p.name: p.read_bytes() for p in directory.iterdir()}


@pytest.fixture
def report_project(tmp_path):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartspace_web.settings")
    django.setup()
    data = empty_data()
    room = Room(7, "Новое название", 2, 40)
    data.rooms.append(room)
    data.sensors.append(Sensor("SENS-7", room, False, 0))
    data.reports.append(Report(
        "REP-old", room, "Старое название", "2026-09-21T10:01:07",
        True, 85, analyze_metric(25.83, 18, 24),
        analyze_metric(49.96, 40, 60), False, "ПРЕДУПРЕЖДЕНИЕ",
    ))
    data.metrics[0].update_limits(100, 200)
    directory = tmp_path / "data"
    save_data(directory, data)
    with override_settings(BASE_DIR=tmp_path, ALLOWED_HOSTS=["testserver"],
                           DEBUG=True):
        yield Client(), data, directory


def test_history_uses_saved_snapshot_and_links_to_current_room(report_project):
    client, data, directory = report_project
    before = snapshot(directory)
    listing = client.get("/reports/")
    assert listing.status_code == 200
    assert 'href="/reports/REP-old/"' in listing.content.decode()
    response = client.get("/reports/REP-old/")
    body = response.content.decode()
    assert response.status_code == 200
    for text in ("Старое название", "25.83 °C", "18–24 °C", "49.96 %",
                 "40–60 %", "85%", "Включён", "ПРЕДУПРЕЖДЕНИЕ"):
        assert text in body
    assert "Новое название" not in body
    assert "100–200" not in body
    assert 'href="/rooms/7/"' in body
    assert "Новое название" in client.get("/rooms/7/").content.decode()
    assert snapshot(directory) == before


@pytest.mark.parametrize("status,temperature,leak,active", [
    ("НОРМА", 21, False, True),
    ("ПРЕДУПРЕЖДЕНИЕ", 27, False, True),
    ("АВАРИЯ", 27, True, True),
    ("НЕТ ДАННЫХ", None, None, False),
])
def test_statuses_and_absent_readings(
        report_project, status, temperature, leak, active):
    client, data, directory = report_project
    data.reports = [Report(
        "REP-test", data.rooms[0], "Историческое помещение",
        "2026-09-21T10:01:07", active, 85,
        analyze_metric(temperature, 18, 24) if active else None,
        analyze_metric(50, 40, 60) if active else None, leak, status,
    )]
    save_data(directory, data)
    before = snapshot(directory)
    for url in ("/reports/", "/reports/REP-test/"):
        response = client.get(url)
        assert response.status_code == 200
        assert status in response.content.decode()
    body = response.content.decode()
    if not active:
        assert body.count("Нет данных") >= 3
        assert "None" not in body and "0 °C" not in body
    else:
        assert ("Не обнаружена" if not leak else "Обнаружена") in body
    assert snapshot(directory) == before


def test_report_names_and_ids_are_escaped(report_project):
    client, data, directory = report_project
    report = data.reports[0]
    report.id = '<img src=x onerror="alert(1)">'
    report.room_name = '<script>alert("room")</script> & старое имя'
    save_data(directory, data)
    url = reverse("report_detail", args=[report.id])
    listing = client.get("/reports/").content.decode()
    assert escape(url) in listing
    response = client.get(url)
    assert response.status_code == 200
    body = response.content.decode()
    for value in (report.id, report.room_name):
        assert value not in body
        assert escape(value) in body
    assert report.room_name not in listing
    assert escape(report.room_name) in listing


def test_missing_report_and_empty_history(report_project):
    client, data, directory = report_project
    data.reports.clear()
    save_data(directory, data)
    before = snapshot(directory)
    response = client.get("/reports/")
    assert response.status_code == 200
    assert "Проверок пока нет" in response.content.decode()
    response = client.get("/reports/REP-missing/")
    assert response.status_code == 404
    assert "Отчёт не найден" in response.content.decode()
    assert 'href="/reports/"' in response.content.decode()
    assert snapshot(directory) == before


@pytest.mark.parametrize("problem", ["broken_json", "journal"])
def test_report_storage_errors_do_not_change_files(report_project, problem):
    client, data, directory = report_project
    if problem == "broken_json":
        (directory / "reports.json").write_text("[broken", encoding="utf-8")
    else:
        backup = {f"{name}.json": None for name in COLLECTIONS}
        (directory / JOURNAL).write_text(json.dumps(backup), encoding="utf-8")
    before = snapshot(directory)
    for url in ("/reports/", "/reports/REP-old/"):
        response = client.get(url)
        assert response.status_code == 503
        body = response.content.decode()
        assert "Данные временно недоступны" in body
        assert str(directory) not in body and "Traceback" not in body
        assert snapshot(directory) == before
