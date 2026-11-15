"""Помещения: список, поиск, связи и отсутствие проверок через ORM."""

import re

from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, render

from reports_web.models import Report
from smartspace_web.query_params import (
    area_value, database_page, date_value, integer,
)
from .models import Room


@database_page
def room_list(request):
    query = request.GET.get("room_id", "").strip()
    min_area = request.GET.get("min_area", "").strip()
    search = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "id")
    orders = {"id": ("id",), "area": ("area", "id"),
              "name": ("name", "id")}
    rooms = Room.objects.all()
    message, style = "", "info"
    try:
        if query:
            rooms = rooms.filter(pk=integer(query, 1))
        if min_area:
            rooms = rooms.filter(area__gte=area_value(min_area))
        if len(search) > 200:
            raise ValueError
        if search:
            # SQLite LIKE нечувствителен к регистру только для ASCII.
            rooms = rooms.filter(name__iregex=re.escape(search))
        if sort not in orders:
            raise ValueError
        rooms = rooms.order_by(*orders[sort])
    except (ValueError, OverflowError):
        rooms = Room.objects.none()
        message = ("Проверьте ID, площадь, название (до 200 символов) "
                   "и выберите сортировку из списка.")
        style = "warning"
    return render(request, "rooms_web/room_list.html", {
        "rooms": rooms, "query": query, "min_area": min_area,
        "search": search, "sort": sort, "message": message,
        "message_style": style, "orm_data": True,
    })


@database_page
def room_detail(request, room_id):
    try:
        room = Room.objects.select_related("sensor").get(pk=room_id)
    except (Room.DoesNotExist, OverflowError):
        room = None
    sensor = getattr(room, "sensor", None)
    return render(request, "rooms_web/room_detail.html", {
        "room": room, "room_id": room_id, "sensor": sensor,
        "available": sensor.is_available() if sensor else False,
    }, status=200 if room else 404)


@database_page
def room_detail_slug(request, slug):
    room = get_object_or_404(Room.objects.select_related("sensor"), slug=slug)
    sensor = getattr(room, "sensor", None)
    return render(request, "rooms_web/room_detail.html", {
        "room": room, "sensor": sensor, "orm_data": True,
        "available": sensor.is_available() if sensor else False,
    })


@database_page
def uninspected_rooms(request):
    selected_date = request.GET.get("date", "").strip()
    rooms, message = Room.objects.none(), ""
    try:
        day = date_value(selected_date)
        if day:
            reports = Report.objects.for_date(
                day).filter(room_id=OuterRef("pk"))
            rooms = Room.objects.filter(~Exists(reports)).order_by("id")
    except ValueError:
        message = "Выберите корректную дату в формате ГГГГ-ММ-ДД."
    return render(request, "rooms_web/uninspected.html", {
        "rooms": rooms, "selected_date": selected_date, "message": message,
    })
