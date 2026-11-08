"""Датчики и текущие помещения одним запросом, без N+1."""

import re

from django.db.models import Q
from django.shortcuts import render

from smartspace_web.query_params import database_page
from .models import Sensor


@database_page
def sensor_list(request):
    available = request.GET.get("available", "")
    search = request.GET.get("q", "").strip()
    sensors = Sensor.objects.select_related("room").order_by("id")
    message = ""
    if available not in ("", "1") or len(search) > 200:
        sensors = Sensor.objects.none()
        message = "Проверьте фильтр и длину поиска (до 200 символов)."
    else:
        if available == "1":
            sensors = sensors.filter(active=True, battery__gt=0)
        if search:
            pattern = re.escape(search)
            sensors = sensors.filter(Q(id__iregex=pattern)
                                     | Q(room__name__iregex=pattern))
    return render(request, "sensors_web/sensor_list.html", {
        "sensors": sensors, "available_only": available == "1",
        "search": search, "message": message, "orm_data": True,
    })
