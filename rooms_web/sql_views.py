"""Помещения из SQLite: SELECT, WHERE, поиск даты и карточка."""

from django.shortcuts import render

from db.database import execute_query
from db.web import (area_value, connection, database_page, date_value,
                    integer)


@database_page
def room_list(request):
    query = request.GET.get("room_id", "").strip()
    min_area = request.GET.get("min_area", "").strip()
    rooms, message, style = [], "", "info"
    try:
        minimum = area_value(min_area) if min_area else 0
        room_id = integer(query, 1) if query else None
    except (ValueError, OverflowError):
        message = ("Введите ID помещения — положительное целое число, "
                   "а площадь — неотрицательное число.")
        style = "warning"
    else:
        with connection() as conn:
            if query:
                rooms = execute_query(conn, "room_search",
                                      (room_id, minimum)).fetchall()
                message = ("Помещение найдено. Нажмите на название, "
                           "чтобы открыть карточку." if rooms else
                           f"Помещение с ID {query} не найдено.")
                style = "success" if rooms else "info"
            elif min_area:
                rooms = execute_query(conn, "rooms_by_area",
                                      (minimum,)).fetchall()
            else:
                rooms = execute_query(conn, "rooms_list").fetchall()
    context = {"rooms": rooms, "query": query, "min_area": min_area,
               "message": message, "message_style": style, "sql_data": True}
    return render(request, "rooms_web/room_list.html", context)


@database_page
def room_detail(request, room_id):
    with connection() as conn:
        room = (execute_query(conn, "room_by_id", (room_id,)).fetchone()
                if room_id <= 9223372036854775807 else None)
        sensor = (execute_query(conn, "sensor_by_room", (room_id,)).fetchone()
                  if room else None)
    context = {"room": room, "room_id": room_id, "sensor": sensor,
               "available": bool(sensor["available"]) if sensor else False}
    return render(request, "rooms_web/room_detail.html", context,
                  status=200 if room else 404)


@database_page
def uninspected_rooms(request):
    selected_date = request.GET.get("date", "").strip()
    rooms, message = [], ""
    try:
        date_value(selected_date)
    except ValueError:
        message = "Выберите корректную дату в формате ГГГГ-ММ-ДД."
    else:
        if selected_date:
            with connection() as conn:
                rooms = execute_query(conn, "rooms_without_reports",
                                      (selected_date,)).fetchall()
    context = {"rooms": rooms, "selected_date": selected_date,
               "message": message}
    return render(request, "rooms_web/uninspected.html", context)
