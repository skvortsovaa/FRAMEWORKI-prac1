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
    # COUNT пагинации, список с JOIN, выбор помещений.
    assert len(queries) == before == 3
    with CaptureQueriesContext(connection) as queries:
        client.get("/sensors/")
    assert len(queries) == 1  # Датчики и помещения загружаются одним JOIN.


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


# ПР10: сценарии интерфейса, прав и миграции данных.
def test_pr10_slug_unique_stable_and_public_links(orm_client):
    client, _ = orm_client
    first = Room.objects.create(name="Серверная № 2", area=49.9)
    second = Room.objects.create(name="Серверная № 2", area=50)
    assert first.slug != second.slug
    assert first.slug.isascii() and first.slug.startswith("servernaia")
    url = first.get_absolute_url()
    assert resolve(url).view_name == "rooms:detail-slug"
    first.name = "Другое название"
    first.save(update_fields=["name"])
    assert first.get_absolute_url() == url
    assert client.get(url).status_code == 200
    assert url in client.get("/rooms/").content.decode()
    assert client.get(f"/rooms/{first.pk}/").status_code == 200
    assert client.get("/rooms/no-such-slug/").status_code == 404


def test_pr10_generated_field_database_recalculates(orm_client):
    room = Room.objects.create(name="Площадь", area=49.9)
    room.refresh_from_db()
    assert room.is_large is False
    from django.db.models import F

    Room.objects.filter(pk=room.pk).update(area=F("area") + 0.1)
    room.refresh_from_db()
    assert room.area == 50 and room.is_large is True
    room.area = 20
    room.save(update_fields=["area"])
    room.refresh_from_db()
    assert room.is_large is False


def test_pr10_manager_statuses_date_and_statistics(orm_client):
    client, _ = orm_client
    room = Room.objects.first()
    day = timezone.localdate()
    records = []
    for number, (status, value, leak) in enumerate([
        (Status.NORMAL, 22, False), (Status.WARNING, 30, False),
        (Status.ALARM, 22, True), (Status.NO_DATA, None, None),
    ]):
        available = value is not None
        report = Report(
            id=f"PR10-{number}", room=room, room_name=room.name,
            checked_at=timezone.now(), sensor_active=available, battery=100,
            status=status, leak_detected=leak,
        )
        if available:
            for metric, val, low, high in [
                ("temperature", value, 18, 24), ("humidity", 50, 40, 60),
            ]:
                for key, item in {"value": val, "minimum": low,
                                  "maximum": high,
                                  "normal": low <= val <= high}.items():
                    setattr(report, f"{metric}_{key}", item)
        report.full_clean()
        report.save()
        records.append(report)
    assert Report.objects.for_date(day).for_room(room).count() == 4
    for method, record in zip(
        ("normal", "warnings", "alarms", "no_data"), records,
    ):
        assert getattr(Report.objects, method)().filter(pk=record.pk).exists()
    assert Report.objects.with_data().for_date(day).count() == 3
    assert Report.objects.filter(pk__in=[r.pk for r in records]).count() == 4
    context = client.get("/reports/statistics/").context
    groups = {r["status"]: r["reports_count"] for r in context["statuses"]}
    assert all(groups[r.status] >= 1 for r in records)
    response = client.get("/reports/", {"date": day.isoformat(),
                                        "status": Status.ALARM})
    assert [r.pk for r in response.context["reports"]] == [records[2].pk]


def test_pr10_context_available_on_multiple_pages_and_database_failure(
        orm_client):
    from django.db import DatabaseError

    client, _ = orm_client
    for url in ("/", "/rooms/", "/reports/", "/sensors/"):
        response = client.get(url)
        assert response.context["site_name"] == "SmartSpace Monitor"
        assert response.context["navigation_rooms_count"] == 2
        assert ">Помещения</a>" in response.content.decode()
    with patch.object(Room.objects, "count", side_effect=DatabaseError):
        assert client.get("/").status_code == 200
        with patch.object(Room.objects, "all", side_effect=DatabaseError):
            assert client.get("/rooms/").status_code == 503


@pytest.fixture
def admin_client(orm_client):
    from django.contrib.auth import get_user_model

    client, source = orm_client
    user = get_user_model().objects.create_superuser(
        "pr10-admin", password=None,
    )
    client.force_login(user)
    return client, source


def test_pr10_admin_lists_inline_and_view_on_site(admin_client):
    from django.contrib import admin

    client, _ = admin_client
    for path in ("rooms_web/room", "sensors_web/sensor", "reports_web/metric",
                 "reports_web/report", "reports_web/reading"):
        assert client.get(f"/admin/{path}/").status_code == 200
    room = Room.objects.get(pk=1)
    response = client.get(f"/admin/rooms_web/room/{room.pk}/change/")
    assert response.status_code == 200
    assert "Датчик" in response.content.decode()
    assert "Отчёт" in response.content.decode()
    assert admin.site._registry[Room].view_on_site
    # Стандартный переход Admin вызывает get_absolute_url().
    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(room)
    response = client.get(f"/admin/r/{ct.pk}/{room.pk}/")
    assert response.status_code == 302
    assert response.url.endswith(room.get_absolute_url())
    report = Report.objects.first()
    body = client.get(
        f"/admin/reports_web/report/{report.pk}/change/"
    ).content.decode()
    assert "Измерения" in body


def test_pr10_admin_search_filter_and_bulk_action_preserve_history(
        admin_client):
    client, _ = admin_client
    room = Room.objects.first()
    report = Report.objects.first()
    before = (report.sensor_active, report.battery, report.status)
    response = client.get("/admin/reports_web/report/", {
        "q": room.name, "status__exact": report.status,
    })
    assert response.context["cl"].result_count == 1
    response = client.post("/admin/sensors_web/sensor/", {
        "action": "disable_sensors", "_selected_action": [room.sensor.pk],
    })
    assert response.status_code == 302
    room.sensor.refresh_from_db()
    assert room.sensor.active is False
    report.refresh_from_db()
    assert (report.sensor_active, report.battery, report.status) == before
    client.post("/admin/sensors_web/sensor/", {
        "action": "enable_sensors", "_selected_action": [room.sensor.pk],
    })
    room.sensor.refresh_from_db()
    assert room.sensor.active is True
    assert client.post(f"/admin/reports_web/report/{report.pk}/change/",
                       {"status": Status.ALARM}).status_code == 403
    assert client.post("/admin/reports_web/report/add/", {}).status_code == 403


def test_pr10_admin_crud_room_and_inline_sensor(admin_client):
    client, _ = admin_client
    payload = {"name": "Тест CRUD", "floor": 2, "area": 60,
               "sensor-TOTAL_FORMS": 0, "sensor-INITIAL_FORMS": 0,
               "reports-TOTAL_FORMS": 0, "reports-INITIAL_FORMS": 0,
               "_save": "Сохранить"}
    response = client.post("/admin/rooms_web/room/add/", payload)
    assert response.status_code == 302
    room = Room.objects.get(name="Тест CRUD")
    assert room.is_large is True and room.slug
    payload.update({"area": 20, "sensor-TOTAL_FORMS": 1,
                    "sensor-0-id": "PR10-INLINE", "sensor-0-active": "on",
                    "sensor-0-battery": 80})
    response = client.post(f"/admin/rooms_web/room/{room.pk}/change/", payload)
    assert response.status_code == 302
    room.refresh_from_db()
    assert room.area == 20 and room.is_large is False
    assert room.sensor.battery == 80
    # PROTECT препятствует удалению помещения с датчиком.
    response = client.post(f"/admin/rooms_web/room/{room.pk}/delete/",
                           {"post": "yes"})
    assert response.status_code == 200 and Room.objects.filter(
        pk=room.pk).exists()
    client.post("/admin/sensors_web/sensor/PR10-INLINE/delete/",
                {"post": "yes"})
    assert client.post(f"/admin/rooms_web/room/{room.pk}/delete/",
                       {"post": "yes"}).status_code == 302
    assert not Room.objects.filter(pk=room.pk).exists()


def test_pr10_staff_view_only_group_and_anonymous_access(orm_client):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group

    client, _ = orm_client
    assert client.get("/admin/").status_code == 302
    call_command("setup_pr10_roles", stdout=StringIO())
    call_command("setup_pr10_roles", stdout=StringIO())
    group = Group.objects.get(name="Наблюдатели SmartSpace")
    assert group.permissions.count() == 5
    user = get_user_model().objects.create_user("observer", is_staff=True)
    user.groups.add(group)
    client.force_login(user)
    assert client.get("/admin/rooms_web/room/").status_code == 200
    assert client.get("/admin/rooms_web/room/add/").status_code == 403
    room = Room.objects.first()
    assert client.post(f"/admin/rooms_web/room/{room.pk}/change/",
                       {"name": "Запрещено"}).status_code == 403
    assert client.post("/admin/sensors_web/sensor/", {
        "action": "disable_sensors", "_selected_action": [room.sensor.pk],
    }).status_code in (200, 302)
    room.sensor.refresh_from_db()
    assert room.sensor.active is True


def test_pr10_upgrade_backfills_duplicate_cyrillic_names(tmp_path):
    import subprocess
    import sys

    code = """
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'smartspace_web.settings'
from django.conf import settings
settings.DATABASES['default']['NAME'] = sys.argv[1]
import django
django.setup()
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
call_command('migrate', 'rooms_web', '0001', verbosity=0)
executor = MigrationExecutor(connection)
OldRoom = executor.loader.project_state(
    [('rooms_web', '0001_initial')]
).apps.get_model('rooms_web', 'Room')
OldRoom.objects.create(pk=1, name='Серверная', floor=1, area=49)
OldRoom.objects.create(pk=2, name='Серверная', floor=2, area=50)
call_command('migrate', verbosity=0)
from rooms_web.models import Room
rows = list(Room.objects.order_by('id'))
assert len(rows) == 2
assert rows[0].slug == 'servernaia-1'
assert rows[1].slug == 'servernaia-2'
assert rows[0].is_large is False and rows[1].is_large is True
assert [(r.name, r.floor, r.area) for r in rows] == [
    ('Серверная', 1, 49), ('Серверная', 2, 50)
]
"""
    subprocess.run(
        [sys.executable, "-c", code, str(tmp_path / "upgrade.sqlite3")],
        check=True, capture_output=True, text=True,
    )
