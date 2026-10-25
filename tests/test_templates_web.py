"""ПР6: контекст, наследование, маршруты и статические ресурсы."""

import os
from unittest.mock import patch

import django
from django.contrib.staticfiles import finders
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import Client, override_settings
from django.test.utils import setup_test_environment, teardown_test_environment
from django.urls import Resolver404, resolve, reverse
import pytest

from models import Room, Sensor
from storage import empty_data, save_data


@pytest.fixture
def template_client(tmp_path):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartspace_web.settings")
    django.setup()
    data = empty_data()
    room = Room(1, "Серверная", 3, 25.5)
    data.rooms.append(room)
    data.sensors.append(Sensor("SENS-1", room))
    save_data(tmp_path / "data", data)
    setup_test_environment()
    try:
        with override_settings(BASE_DIR=tmp_path,
                               ALLOWED_HOSTS=["testserver"], DEBUG=False):
            yield Client()
    finally:
        teardown_test_environment()


@pytest.mark.parametrize("url,template", [
    ("/", "homepage/index.html"),
    ("/rooms/", "rooms_web/room_list.html"),
    ("/rooms/1/", "rooms_web/room_detail.html"),
    ("/sensors/", "sensors_web/sensor_list.html"),
    ("/reports/", "reports_web/report_list.html"),
])
def test_pages_inherit_base_and_navigation(template_client, url, template):
    response = template_client.get(url)
    assert response.status_code == 200
    names = {item.name for item in response.templates}
    assert {template, "base.html", "includes/navigation.html"} <= names
    body = response.content.decode()
    for resource in ("css/style.css", "js/main.js", "img/logo.svg"):
        assert f"/static/homepage/{resource}" in body
    assert 'id="current-year"' in body


def test_room_context_contains_domain_objects(template_client):
    listing = template_client.get("/rooms/")
    assert isinstance(listing.context["rooms"][0], Room)
    assert "rooms_web/includes/room_card.html" in {
        item.name for item in listing.templates
    }
    detail = template_client.get("/rooms/1/")
    assert detail.context["sensor"].room is detail.context["room"]
    assert detail.context["available"] is True


@pytest.mark.parametrize("url,template,heading", [
    ("/rooms/999/", "rooms_web/room_detail.html", "Помещение не найдено"),
    ("/reports/absent/", "reports_web/report_detail.html", "Отчёт не найден"),
    ("/unknown/", "404.html", "404 — страница не найдена"),
    ("/rooms/text/", "404.html", "404 — страница не найдена"),
])
def test_template_404_responses(template_client, url, template, heading):
    response = template_client.get(url)
    assert response.status_code == 404
    assert template in {item.name for item in response.templates}
    assert heading in response.content.decode()


def test_storage_error_uses_shared_template(template_client):
    with patch("rooms_web.views.load_project_data", side_effect=ValueError):
        response = template_client.get("/rooms/")
    assert response.status_code == 503
    assert "homepage/data_unavailable.html" in {
        item.name for item in response.templates
    }


def test_namespaces_and_integer_converter(template_client):
    assert reverse("homepage:index") == "/"
    assert reverse("rooms:list") == "/rooms/"
    assert reverse("rooms:detail", args=[7]) == "/rooms/7/"
    assert reverse("sensors:list") == "/sensors/"
    assert reverse("reports:list") == "/reports/"
    assert reverse("reports:detail", args=["REP-7"]) == "/reports/REP-7/"
    match = resolve("/rooms/7/")
    assert match.view_name == "rooms:detail"
    assert match.kwargs == {"room_id": 7}
    with pytest.raises(Resolver404):
        resolve("/rooms/text/")


def test_default_and_missing_variables(template_client):
    body = render_to_string("rooms_web/includes/room_card.html", {
        "room": {"id": 1, "name": "", "floor": 0, "area": 12},
    })
    assert "Без названия" in body
    assert Template("[{{ absent }}]").render(Context()) == "[]"


def test_static_resources_are_discoverable(template_client):
    for name in ("css/style.css", "js/main.js", "img/logo.svg"):
        assert finders.find(f"homepage/{name}")
