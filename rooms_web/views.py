"""Подготовка объектов помещений для шаблонов без записи в JSON."""

from django.conf import settings
from django.shortcuts import render

from . import orm_views, sql_views

from homepage.views import data_unavailable
from models.rooms import get_room
from models.sensors import get_room_sensor
from smartspace_web.data import load_project_data


def room_list(request):
    """Список помещений с прежним поиском по положительному ID."""
    if settings.SMARTSPACE_DATA_SOURCE == "orm":
        return orm_views.room_list(request)
    if settings.SMARTSPACE_DATA_SOURCE == "sqlite":
        return sql_views.room_list(request)
    try:
        data = load_project_data()
    except (OSError, ValueError):
        return data_unavailable(request)

    query = request.GET.get("room_id", "").strip()
    rooms = data.rooms
    message = ""
    message_style = "info"
    if query:
        rooms = []
        try:
            if not query.isascii() or not query.isdecimal():
                raise ValueError
            room_id = int(query)
            if room_id <= 0:
                raise ValueError
        except ValueError:
            message = (
                "Введите ID помещения — положительное целое число, "
                "например 1."
            )
            message_style = "warning"
        else:
            try:
                rooms = [get_room(data.rooms, room_id)]
            except ValueError:
                message = f"Помещение с ID {query} не найдено."
            else:
                message = (
                    "Помещение найдено. Нажмите на название, "
                    "чтобы открыть карточку."
                )
                message_style = "success"

    context = {
        "rooms": rooms,
        "query": query,
        "message": message,
        "message_style": message_style,
    }
    return render(request, "rooms_web/room_list.html", context)


def room_detail(request, room_id):
    """Объект или None передаётся в шаблон; HTTP-статус выбирает view."""
    if settings.SMARTSPACE_DATA_SOURCE == "orm":
        return orm_views.room_detail(request, room_id)
    if settings.SMARTSPACE_DATA_SOURCE == "sqlite":
        return sql_views.room_detail(request, room_id)
    try:
        data = load_project_data()
    except (OSError, ValueError):
        return data_unavailable(request)

    try:
        room = get_room(data.rooms, room_id)
    except ValueError:
        room = None
    sensor = get_room_sensor(data.sensors, room.id) if room else None
    context = {
        "room": room,
        "room_id": room_id,
        "sensor": sensor,
        "available": sensor.is_available() if sensor else False,
    }
    return render(
        request, "rooms_web/room_detail.html", context,
        status=404 if room is None else 200,
    )


def uninspected_rooms(request):
    if settings.SMARTSPACE_DATA_SOURCE == "orm":
        return orm_views.uninspected_rooms(request)
    return sql_views.uninspected_rooms(request)
