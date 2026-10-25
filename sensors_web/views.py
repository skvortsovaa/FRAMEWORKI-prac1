"""Отображение объектов Sensor и их связей с помещениями."""

from django.shortcuts import render

from homepage.views import data_unavailable
from smartspace_web.data import load_project_data


def sensor_list(request):
    """Шаблон вызывает метод Sensor.is_available без аргументов."""
    try:
        data = load_project_data()
    except (OSError, ValueError):
        return data_unavailable(request)
    context = {"sensors": data.sensors}
    return render(request, "sensors_web/sensor_list.html", context)
