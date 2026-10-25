"""JOIN помещений и датчиков, фильтр по доступности."""

from django.shortcuts import render

from db.database import execute_query
from db.web import connection, database_page


@database_page
def sensor_list(request):
    available = request.GET.get("available", "") == "1"
    query = "available_sensors" if available else "sensors_with_rooms"
    with connection() as conn:
        sensors = execute_query(conn, query).fetchall()
    return render(request, "sensors_web/sensor_list.html", {
        "sensors": sensors, "available_only": available, "sql_data": True,
    })
