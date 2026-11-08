"""Отображение объектов Sensor и их связей с помещениями."""

from django.conf import settings
from django.shortcuts import render

from . import orm_views, sql_views

from homepage.views import data_unavailable
from smartspace_web.data import load_project_data


def sensor_list(request):
    """Шаблон вызывает метод Sensor.is_available без аргументов."""
    if settings.SMARTSPACE_DATA_SOURCE == "orm":
        return orm_views.sensor_list(request)
    if settings.SMARTSPACE_DATA_SOURCE == "sqlite":
        return sql_views.sensor_list(request)
    try:
        data = load_project_data()
    except (OSError, ValueError):
        return data_unavailable(request)
    context = {"sensors": data.sensors}
    return render(request, "sensors_web/sensor_list.html", context)
