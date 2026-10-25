"""История, агрегаты и группировки SQLite без Django ORM."""

from django.shortcuts import render

from db.database import execute_query
from db.web import (STATUSES, connection, database_page, date_value,
                    integer)


@database_page
def report_list(request):
    selected_date = request.GET.get("date", "").strip()
    status = request.GET.get("status", "").strip()
    reports, message = [], ""
    try:
        date_value(selected_date)
        if status and status not in STATUSES:
            raise ValueError("Неизвестный статус.")
    except ValueError:
        message = "Выберите корректную дату и статус из списка."
    else:
        with connection() as conn:
            if selected_date or status:
                reports = execute_query(conn, "reports_filtered", (
                    selected_date, selected_date, status, status,
                )).fetchall()
            else:
                reports = execute_query(conn, "reports_with_rooms").fetchall()
    context = {"reports": reports, "selected_date": selected_date,
               "selected_status": status, "statuses": STATUSES,
               "message": message, "sql_data": True}
    return render(request, "reports_web/report_list.html", context)


@database_page
def report_detail(request, report_id):
    with connection() as conn:
        row = execute_query(conn, "report_by_id", (report_id,)).fetchone()
    report = dict(row) if row else None
    if report:
        report["leak_detected"] = (None if report["leak_detected"] is None
                                   else bool(report["leak_detected"]))
        for metric in ("temperature", "humidity"):
            report[metric] = (
                {field: report[f"{metric}_{field}"]
                 for field in ("value", "minimum", "maximum", "normal")}
                if report[f"{metric}_value"] is not None else None
            )
    return render(request, "reports_web/report_detail.html", {
        "report": report, "sql_data": True,
    }, status=200 if report else 404)


@database_page
def statistics(request):
    threshold = request.GET.get("min_count", "0").strip()
    message = ""
    try:
        min_count = integer(threshold)
    except ValueError:
        min_count = 0
        message = "Порог должен быть неотрицательным целым числом."
    with connection() as conn:
        context = {
            "rooms_total": execute_query(conn, "room_count").fetchone(),
            "totals": execute_query(conn, "report_totals").fetchone(),
            "statistics": execute_query(conn, "room_report_counts").fetchall(),
            "statuses": execute_query(conn, "status_counts").fetchall(),
            "filtered": execute_query(conn, "rooms_above_count",
                                      (min_count,)).fetchall(),
            "metrics": execute_query(conn, "metric_statistics").fetchall(),
            "threshold": threshold, "message": message,
        }
    return render(request, "reports_web/statistics.html", context)


@database_page
def readings(request):
    limit = request.GET.get("limit", "10").strip()
    offset = request.GET.get("offset", "0").strip()
    message = ""
    try:
        page_size = integer(limit, 1, 100)
        start = integer(offset, 0, 1000000)
    except ValueError:
        page_size, start = 10, 0
        message = "Размер страницы: 1–100, сдвиг: 0–1000000."
    with connection() as conn:
        rows = execute_query(conn, "readings_list",
                             (page_size, start)).fetchall()
        metrics = execute_query(conn, "metrics_list").fetchall()
    return render(request, "reports_web/readings.html", {
        "readings": rows, "metrics": metrics, "limit": limit,
        "offset": offset, "message": message,
    })
