"""ПР9: настоящие миграции, перенос, ORM и веб на изолированной базе."""

from contextlib import closing
from datetime import timedelta
from io import StringIO
import os
from pathlib import Path
import shutil
import sqlite3
from unittest.mock import patch

import django
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, override_settings
from django.test.utils import (
    CaptureQueriesContext, setup_databases, setup_test_environment,
    teardown_databases, teardown_test_environment,
)
from django.utils import timezone
from django.urls import resolve
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartspace_web.settings")
django.setup()

from db.import_sqlite_to_orm import import_source, normalize, read_source  # noqa
from reports_web.models import Metric, Reading, Report, Status  # noqa
from rooms_web.models import Room  # noqa
from sensors_web.models import Sensor  # noqa


@pytest.fixture(scope="module")
def orm_database():
    old_config = setup_databases(verbosity=0, interactive=False)
    try:
        yield
    finally:
        teardown_databases(old_config, verbosity=0)


@pytest.fixture
def orm_client(orm_database, tmp_path):
    # Импорт URL/view до patch: иначе первый импорт захватит mock навсегда.
    resolve("/reports/")
    setup_test_environment()
    source = tmp_path / "source.sqlite"
    shutil.copyfile(Path(__file__).resolve().parents[1]
                    / "data/smartspace.sqlite", source)
    try:
        with transaction.atomic(), override_settings(
            SMARTSPACE_DATA_SOURCE="orm", ALLOWED_HOSTS=["testserver"],
        ):
            import_source(source)
            yield Client(), source
            transaction.set_rollback(True)
    finally:
        teardown_test_environment()


def test_import_preserves_every_field_links_and_source(orm_client):
    _, source = orm_client
    before = source.read_bytes()
    rows = read_source(source)
    models = {"rooms": Room, "sensors": Sensor, "metrics": Metric,
              "reports": Report, "readings": Reading}
    for name, model in models.items():
        assert model.objects.count() == len(rows[name])
        for row in rows[name]:
            expected = normalize(model, row)
            obj = model.objects.get(pk=row["id"])
            assert all(getattr(obj, key) == val
                       for key, val in expected.items())
    assert import_source(source) == {
        key: len(val) for key, val in rows.items()
    }
    assert source.read_bytes() == before
    reading = Reading.objects.select_related("sensor__room", "report").first()
    assert reading.sensor.room_id == reading.report.room_id


def test_conflicting_import_is_atomic_and_update_is_explicit(orm_client):
    _, source = orm_client
    with closing(sqlite3.connect(source)) as conn, conn:
        conn.execute("INSERT INTO rooms VALUES (100, 'New', 1, 20)")
        conn.execute("UPDATE reports SET room_name = 'Different'")
    original = Report.objects.first().room_name
    with pytest.raises(ValueError, match="--update"):
        import_source(source)
    assert not Room.objects.filter(pk=100).exists()
    assert Report.objects.first().room_name == original
    import_source(source, update=True)
    assert Room.objects.filter(pk=100).exists()
    assert Report.objects.first().room_name == "Different"


def test_invalid_source_rolls_back_prior_inserts(orm_client):
    _, source = orm_client
    with closing(sqlite3.connect(source)) as conn, conn:
        conn.execute("PRAGMA ignore_check_constraints=ON")
        conn.execute("INSERT INTO rooms VALUES (100, 'Valid', 1, 20)")
        conn.execute("INSERT INTO rooms VALUES (101, '   ', 1, 20)")
    with pytest.raises(ValidationError):
        import_source(source)
    assert not Room.objects.filter(pk__gte=100).exists()


def test_missing_source_is_not_created(orm_client, tmp_path):
    path = tmp_path / "missing.sqlite"
    with pytest.raises((OSError, sqlite3.Error)):
        import_source(path)
    assert not path.exists()


def test_crud_constraints_and_snapshot(orm_client):
    room = Room.objects.create(name="CRUD", floor=-1, area=15)
    room.area = 20
    room.full_clean()
    room.save()
    assert Room.objects.get(pk=room.pk).area == 20
    sensor = Sensor.objects.create(id="CRUD-S", room=room)
    assert room.sensor.pk == sensor.pk
    sensor.battery = 101
    with pytest.raises(ValidationError):
        sensor.full_clean()
    with pytest.raises(ProtectedError):
        room.delete()
    sensor.delete()
    key = room.pk
    room.delete()
    assert not Room.objects.filter(pk=key).exists()
    report = Report.objects.first()
    snapshot = (report.room_name, report.temperature.copy())
    report.room.name = "Новое название"
    report.room.save()
    Metric.objects.filter(pk="temperature").update(minimum=-10)
    report.refresh_from_db()
    assert (report.room_name, report.temperature) == snapshot
    with pytest.raises(ProtectedError):
        report.delete()


def test_demo_command_does_not_change_database(orm_client):
    before = list(Room.objects.values())
    out = StringIO()
    call_command("demo_orm", stdout=out)
    assert "PROTECT" in out.getvalue() and "ROLLBACK" in out.getvalue()
    assert list(Room.objects.values()) == before


@pytest.mark.parametrize("url", [
    "/", "/rooms/", "/rooms/1/", "/sensors/", "/reports/",
    "/rooms/uninspected/?date=2026-09-21", "/reports/statistics/",
    "/reports/readings/?limit=2&offset=1",
])
def test_pages_use_orm_without_legacy_storage(orm_client, url):
    client, _ = orm_client
    with patch("db.database.get_connection", side_effect=AssertionError), \
            patch("db.database.execute_query", side_effect=AssertionError), \
            patch("smartspace_web.data.load_project_data",
                  side_effect=AssertionError):
        assert client.get(url).status_code == 200


def test_detail_dates_null_zero_and_missing_objects(orm_client):
    client, _ = orm_client
    report = Report.objects.first()
    response = client.get(f"/reports/{report.pk}/")
    body = response.content.decode()
    assert "21.09.2026 10:01:07" in body
    assert "Не обнаружена" in body  # False не превращается в NULL.
    for url in ("/rooms/99999/", "/reports/missing/",
                "/rooms/99999999999999999999999999/"):
        assert client.get(url).status_code == 404
    room = Room.objects.create(name="Без датчика", area=5)
    assert "Датчик ещё не установлен" in client.get(
        f"/rooms/{room.pk}/",
    ).content.decode()


def test_search_filters_and_sorting(orm_client):
    client, _ = orm_client
    room = Room.objects.create(name="Server Annex", area=100, floor=2)
    Sensor.objects.create(id="EXTRA", room=room, active=False)
    response = client.get("/rooms/", {"q": "server", "min_area": 50})
    assert [r.pk for r in response.context["rooms"]] == [room.pk]
    response = client.get("/sensors/", {"q": "Annex"})
    assert [s.pk for s in response.context["sensors"]] == ["EXTRA"]
    response = client.get("/sensors/", {"q": "Annex", "available": 1})
    assert not response.context["sensors"]
    areas = [r.area for r in client.get("/rooms/?sort=area").context["rooms"]]
    assert areas == sorted(areas)
    response = client.get("/rooms/", {"q": "серверная"})
    assert [r.pk for r in response.context["rooms"]] == [1]
    response = client.get("/rooms/", {"q": ".*"})
    assert not response.context["rooms"]  # Поиск буквального текста.


def add_history(room, count=13):
    day = timezone.make_aware(timezone.datetime(2026, 10, 1, 0, 30))
    for index in range(count):
        Report.objects.create(id=f"PAGE-{index:02}", room=room,
                              room_name="Историческое имя",
                              sensor_active=False,
                              battery=0,
                              checked_at=day + timedelta(minutes=index),
                              status=Status.NO_DATA)


def test_combined_filters_pagination_and_querystrings(orm_client):
    client, _ = orm_client
    room = Room.objects.create(name="Новое имя", area=12)
    add_history(room)
    params = {"room_id": room.pk, "date": "2026-10-01",
              "status": "НЕТ ДАННЫХ", "q": "Историческое", "sort": "oldest",
              "page_size": 5, "page": 2}
    response = client.get("/reports/", params)
    assert response.context["page_obj"].paginator.count == 13
    assert [r.pk for r in response.context["reports"]] == [
        f"PAGE-{n:02}" for n in range(5, 10)
    ]
    body = response.content.decode()
    assert all(part in body for part in
               ("page=3", "sort=oldest", "date=2026-10-01"))
    assert "room_id=" in body and "page_size=5" in body
    for page, expected in (("nonsense", 1), ("9999", 3), ("0", 3)):
        params["page"] = page
        page_obj = client.get("/reports/", params).context["page_obj"]
        assert page_obj.number == expected
    params["exclude_no_data"] = 1
    response = client.get("/reports/", params)
    assert response.context["page_obj"].paginator.count == 0
    # Фильтрация по текущему имени связанной модели.
    response = client.get("/reports/?q=Новое")
    assert response.context["page_obj"].paginator.count == 13


def test_statistics_zero_groups_and_uninspected(orm_client):
    client, _ = orm_client
    room = Room.objects.create(name="Без проверок", area=10)
    context = client.get("/reports/statistics/").context
    assert context["totals"]["total"] == Report.objects.count()
    assert context["rooms_total"]["total_area"] == sum(
        Room.objects.values_list("area", flat=True)
    )
    groups = {row["id"]: row["reports_count"] for row in context["statistics"]}
    assert groups[room.pk] == 0
    assert room.pk not in [row["id"] for row in context["filtered"]]
    response = client.get("/rooms/uninspected/?date=2026-09-21")
    assert room.pk in [r.pk for r in response.context["rooms"]]
    assert 1 not in [r.pk for r in response.context["rooms"]]


def test_related_queries_do_not_grow_with_rows(orm_client):
    client, _ = orm_client
    room = Room.objects.first()
    with CaptureQueriesContext(connection) as queries:
        client.get("/reports/")
    before = len(queries)
    add_history(room)
    with CaptureQueriesContext(connection) as queries:
        client.get("/reports/?page_size=100")
    # COUNT, список с JOIN, выбор помещений.
    assert len(queries) == before == 3
    with CaptureQueriesContext(connection) as queries:
        client.get("/sensors/")
    assert len(queries) == 1


@pytest.mark.parametrize("url", [
    "/rooms/?room_id=-1", "/rooms/?min_area=nan", "/rooms/?sort=bad",
    "/reports/?date=2026-02-30", "/reports/?sort=room__password",
    "/reports/?status=bad", "/reports/?page_size=0",
    "/reports/?room_id=99999999999999999999999999",
    "/reports/?exclude_no_data=bad", "/sensors/?available=bad",
    "/reports/readings/?limit=101", "/reports/statistics/?min_count=-1",
    "/rooms/uninspected/?date=bad",
])
def test_invalid_parameters_show_message(orm_client, url):
    response = orm_client[0].get(url)
    assert response.status_code == 200
    assert response.context["message"]


def test_empty_database_and_database_failure(orm_client):
    client, _ = orm_client
    for model in (Reading, Report, Sensor, Metric, Room):
        model.objects.all().delete()
    for url in ("/rooms/", "/sensors/", "/reports/", "/reports/statistics/",
                "/reports/readings/", "/rooms/uninspected/?date=2026-10-01"):
        assert client.get(url).status_code == 200
    context = client.get("/reports/statistics/").context
    assert context["totals"] == {"total": 0, "alarms": 0, "no_data": 0}
    assert context["rooms_total"] == {"total": 0, "total_area": 0}
    from django.db import OperationalError
    with patch.object(Room.objects, "all", side_effect=OperationalError):
        assert client.get("/rooms/").status_code == 503
