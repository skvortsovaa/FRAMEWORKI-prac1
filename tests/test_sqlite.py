"""ПР7: импорт, ограничения SQLite и реальный SQL-путь веб-запроса."""

from contextlib import closing
import os
import sqlite3
from unittest.mock import patch

import django
from django.test import Client, override_settings
from django.test.utils import setup_test_environment, teardown_test_environment
import pytest

from db.database import execute_query, get_connection, initialize_database
from db.import_json import import_data, prepare_rows
from models import Report, Room, Sensor
from models.metrics import analyze_metric
from models.readings import record_report_readings
from storage import empty_data, save_data


@pytest.fixture
def sql_project(tmp_path):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartspace_web.settings")
    django.setup()
    data = empty_data()
    data.rooms = [Room(1, "Текущее имя", 3, 25.5),
                  Room(2, "Архив", 2, 40), Room(3, "Лаборатория", 1, 55),
                  Room(4, "Без проверок", 0, 15)]
    data.sensors = [Sensor(f"SENS-{i}", room, i != 3,
                           0 if i == 3 else 15 if i == 2 else 85)
                    for i, room in enumerate(data.rooms, 1)]
    data.reports = [
        Report("REP-1", data.rooms[0], "Историческое имя",
               "2026-09-21T10:01:07", True, 85,
               analyze_metric(25.83, 18, 24), analyze_metric(49.96, 40, 60),
               False, "ПРЕДУПРЕЖДЕНИЕ"),
        Report("REP-2", data.rooms[1], "Архив", "2026-09-22T10:00:00",
               True, 15, analyze_metric(21, 18, 24),
               analyze_metric(50, 40, 60), False, "НОРМА"),
        Report("REP-3", data.rooms[2], "Лаборатория", "2026-09-21T11:00:00",
               False, 0, None, None, None, "НЕТ ДАННЫХ"),
    ]
    for report, sensor in zip(data.reports, data.sensors):
        record_report_readings(data.readings, sensor, data.metrics, report)
    source = tmp_path / "json"
    save_data(source, data)
    database = tmp_path / "smartspace.sqlite"
    import_data(source, database)
    setup_test_environment()
    try:
        with override_settings(SMARTSPACE_DATA_SOURCE="sqlite",
                               SMARTSPACE_DB_PATH=database,
                               ALLOWED_HOSTS=["testserver"], DEBUG=False):
            yield Client(), source, database, data
    finally:
        teardown_test_environment()


def tables(database):
    with closing(get_connection(database)) as conn:
        return {name: [tuple(r) for r in conn.execute(
            f"SELECT * FROM {name} ORDER BY id"
        )] for name in ("rooms", "sensors", "metrics", "reports", "readings")}


def test_import_counts_idempotence_and_source_unchanged(sql_project):
    _, source, database, _ = sql_project
    source_before = {p.name: p.read_bytes() for p in source.iterdir()}
    before = tables(database)
    counts = import_data(source, database)
    initialize_database(database)
    assert counts == {"rooms": 4, "sensors": 4, "metrics": 3,
                      "reports": 3, "readings": 6}
    assert tables(database) == before
    assert {p.name: p.read_bytes() for p in source.iterdir()} == source_before


@pytest.mark.parametrize("sql", [
    "INSERT INTO sensors VALUES ('bad', 999, 1, 80)",
    "INSERT INTO sensors VALUES ('duplicate-room', 1, 1, 80)",
    "UPDATE sensors SET battery = 101 WHERE id = 'SENS-1'",
    "UPDATE rooms SET area = -1 WHERE id = 1",
    "DELETE FROM rooms WHERE id = 1",
])
def test_schema_enforces_relationships_and_values(sql_project, sql):
    _, _, database, _ = sql_project
    before = tables(database)
    with closing(get_connection(database)) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql)
        conn.rollback()
    assert tables(database) == before


def test_import_refuses_to_overwrite_changed_database(sql_project):
    _, source, database, _ = sql_project
    with closing(get_connection(database)) as conn, conn:
        conn.execute("UPDATE rooms SET name = ? WHERE id = ?", ("Из БД", 1))
    before = tables(database)
    with pytest.raises(ValueError, match="--replace"):
        import_data(source, database)
    assert tables(database) == before


def test_failed_replace_rolls_back_all_tables(sql_project):
    _, source, database, _ = sql_project
    before = tables(database)
    with closing(get_connection(database)) as conn:
        conn.execute("""CREATE TRIGGER stop_import BEFORE INSERT ON readings
                     BEGIN SELECT RAISE(ABORT, 'test import failure'); END""")
    rows = prepare_rows(source)
    rows["rooms"][0] = (1, "Другой источник", 3, 25.5)
    with patch("db.import_json.prepare_rows", return_value=rows):
        with pytest.raises(sqlite3.IntegrityError):
            import_data(source, database, replace=True)
    assert tables(database) == before


def test_invalid_json_does_not_modify_database(sql_project):
    _, source, database, _ = sql_project
    before = tables(database)
    (source / "rooms.json").write_text("[broken", encoding="utf-8")
    with pytest.raises(ValueError):
        import_data(source, database, replace=True)
    assert tables(database) == before


def test_readonly_missing_file_is_not_created(tmp_path):
    path = tmp_path / "missing.sqlite"
    with pytest.raises(sqlite3.OperationalError):
        get_connection(path, read_only=True)
    assert not path.exists()


def test_row_factory_and_live_sql_data(sql_project):
    client, source, database, _ = sql_project
    with closing(get_connection(database)) as conn, conn:
        row = execute_query(conn, "room_by_id", (1,)).fetchone()
        assert isinstance(row, sqlite3.Row)
        assert row["name"] == "Текущее имя"
        conn.execute("UPDATE rooms SET name = ? WHERE id = ?", ("Из БД", 1))
    # JSON deliberately becomes unreadable: the live web still uses SQLite.
    (source / "rooms.json").write_text("[broken", encoding="utf-8")
    response = client.get("/rooms/")
    assert response.status_code == 200
    assert isinstance(response.context["rooms"][0], sqlite3.Row)
    assert "Из БД" in response.content.decode()


@pytest.mark.parametrize("path", [
    "/", "/rooms/", "/rooms/1/", "/sensors/", "/reports/",
    "/reports/REP-1/", "/reports/REP-3/", "/rooms/uninspected/",
    "/reports/statistics/", "/reports/readings/",
])
def test_sql_pages_open(sql_project, path):
    client, _, database, _ = sql_project
    before = database.read_bytes()
    assert client.get(path).status_code == 200
    assert database.read_bytes() == before


def test_area_sensor_and_report_filters(sql_project):
    client, _, _, _ = sql_project
    response = client.get("/rooms/", {"min_area": "30"})
    assert {row["id"] for row in response.context["rooms"]} == {2, 3}
    response = client.get("/sensors/", {"available": "1"})
    assert len(response.context["sensors"]) == 3
    response = client.get("/reports/", {
        "date": "2026-09-21", "status": "ПРЕДУПРЕЖДЕНИЕ",
    })
    assert [row["id"] for row in response.context["reports"]] == ["REP-1"]
    assert "Текущее имя" in response.content.decode()
    assert "Историческое имя" in response.content.decode()


def test_uninspected_rooms_and_empty_search(sql_project):
    client, _, _, _ = sql_project
    response = client.get("/rooms/uninspected/", {"date": "2026-09-21"})
    assert {row["id"] for row in response.context["rooms"]} == {2, 4}
    response = client.get("/rooms/", {"min_area": "9999"})
    assert response.context["rooms"] == []
    assert response.status_code == 200


def test_statistics_left_join_having_and_zero_aggregates(sql_project):
    client, _, database, _ = sql_project
    response = client.get("/reports/statistics/", {"min_count": "1"})
    assert response.context["rooms_total"]["total"] == 4
    assert response.context["totals"]["total"] == 3
    assert {r["id"]: r["reports_count"]
            for r in response.context["statistics"]} == {
                1: 1, 2: 1, 3: 1, 4: 0,
            }
    assert response.context["filtered"] == []
    with closing(get_connection(database)) as conn, conn:
        conn.execute("DELETE FROM readings")
        conn.execute("DELETE FROM reports")
    response = client.get("/reports/statistics/")
    assert response.context["totals"]["total"] == 0
    assert response.context["totals"]["alarms"] == 0
    assert all(r["minimum_value"] is None
               for r in response.context["metrics"])


def test_snapshot_null_and_false_are_distinct(sql_project):
    client, _, _, _ = sql_project
    body = client.get("/reports/REP-1/").content.decode()
    for value in ("Историческое имя", "25.83 °C", "18–24 °C",
                  "49.96 %", "Не обнаружена"):
        assert value in body
    body = client.get("/reports/REP-3/").content.decode()
    assert body.count("Нет данных") >= 3
    assert "None" not in body


def test_pagination_is_deterministic(sql_project):
    client, _, _, _ = sql_project
    first = client.get("/reports/readings/", {"limit": "2", "offset": "0"})
    second = client.get("/reports/readings/", {"limit": "2", "offset": "2"})
    assert len(first.context["readings"]) == 2
    assert not {r["id"] for r in first.context["readings"]} & {
        r["id"] for r in second.context["readings"]
    }


@pytest.mark.parametrize("path,params", [
    ("/rooms/", {"room_id": "1 OR 1=1"}),
    ("/rooms/", {"min_area": "nan"}),
    ("/rooms/", {"room_id": "9" * 100}),
    ("/reports/", {"status": "' OR 1=1 --"}),
    ("/reports/", {"date": "2026-02-30"}),
    ("/reports/statistics/", {"min_count": "-1"}),
    ("/reports/readings/", {"limit": "9" * 5000}),
])
def test_invalid_user_parameters_are_safe(sql_project, path, params):
    client, _, database, _ = sql_project
    before = database.read_bytes()
    response = client.get(path, params)
    assert response.status_code == 200
    assert database.read_bytes() == before


@pytest.mark.parametrize("path", [
    "/rooms/999/", "/rooms/text/", "/reports/missing/",
    "/rooms/" + "9" * 50 + "/",
])
def test_sql_not_found(sql_project, path):
    assert sql_project[0].get(path).status_code == 404


@pytest.mark.parametrize("path", [
    "/rooms/", "/sensors/", "/reports/", "/reports/statistics/",
    "/reports/readings/",
])
def test_missing_sqlite_returns_safe_503(sql_project, tmp_path, path):
    with override_settings(SMARTSPACE_DB_PATH=tmp_path / "missing.sqlite"):
        response = sql_project[0].get(path)
    assert response.status_code == 503
    assert "Данные временно недоступны" in response.content.decode()
    assert not (tmp_path / "missing.sqlite").exists()
