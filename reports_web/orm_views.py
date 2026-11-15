"""История, поиск, статистика и постраничный вывод средствами ORM."""

import re

from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.shortcuts import render

from rooms_web.models import Room
from smartspace_web.query_params import database_page, date_value, integer
from .models import Metric, Reading, Report, Status


REPORT_ORDERS = {
    "newest": ("-checked_at", "id"),
    "oldest": ("checked_at", "id"),
    "room": ("room__name", "-checked_at", "id"),
    "status": ("status", "-checked_at", "id"),
}
SORT_LABELS = {"newest": "Сначала новые", "oldest": "Сначала старые",
               "room": "По помещению", "status": "По статусу"}


@database_page
def report_list(request):
    selected_date = request.GET.get("date", "").strip()
    status = request.GET.get("status", "").strip()
    room_id = request.GET.get("room_id", "").strip()
    search = request.GET.get("q", "").strip()
    exclude_no_data = request.GET.get("exclude_no_data", "")
    sort = request.GET.get("sort", "newest")
    page_size = request.GET.get("page_size", "10")
    reports = Report.objects.select_related("room")
    message = ""
    size = 10
    try:
        day = date_value(selected_date)
        if (status and status not in Status.values
                or exclude_no_data not in ("", "1")
                or sort not in REPORT_ORDERS or len(search) > 200):
            raise ValueError
        size = integer(page_size, 1, 100)
        if day:
            reports = reports.for_date(day)
        if status:
            reports = reports.filter(status=status)
        if room_id:
            reports = reports.for_room(integer(room_id, 1))
        if exclude_no_data == "1":
            reports = reports.with_data()
        if search:
            pattern = re.escape(search)
            reports = reports.filter(Q(room_name__iregex=pattern)
                                     | Q(room__name__iregex=pattern)
                                     | Q(id__iregex=pattern))
        reports = reports.order_by(*REPORT_ORDERS[sort])
    except (ValueError, OverflowError):
        reports = Report.objects.none()
        message = ("Проверьте дату, ID помещения, поиск, статус, сортировку "
                   "и размер страницы (1–100).")
    page_obj = Paginator(reports, size).get_page(request.GET.get("page"))
    return render(request, "reports_web/report_list.html", {
        "reports": page_obj, "page_obj": page_obj,
        "selected_date": selected_date, "selected_status": status,
        "selected_room": room_id, "statuses": Status.values,
        "rooms": Room.objects.values("id", "name").order_by("name", "id"),
        "search": search, "exclude_no_data": exclude_no_data == "1",
        "sort": sort, "sort_options": SORT_LABELS.items(),
        "page_size": page_size, "message": message, "orm_data": True,
    })


@database_page
def report_detail(request, report_id):
    try:
        report = Report.objects.select_related("room").get(pk=report_id)
    except Report.DoesNotExist:
        report = None
    return render(request, "reports_web/report_detail.html", {
        "report": report, "orm_data": True,
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
    counts = Room.objects.values("id", room_name=F("name")).annotate(
        reports_count=Count("reports"),
    ).order_by("-reports_count", "id")
    return render(request, "reports_web/statistics.html", {
        "rooms_total": Room.objects.aggregate(
            total=Count("id"), total_area=Sum("area", default=0),
        ),
        "totals": Report.objects.aggregate(
            total=Count("id"),
            alarms=Count("id", filter=Q(status=Status.ALARM)),
            no_data=Count("id", filter=Q(status=Status.NO_DATA)),
        ),
        "statistics": counts,
        "statuses": Report.objects.values("status").annotate(
            reports_count=Count("id"),
        ).order_by("-reports_count", "status"),
        "filtered": counts.filter(reports_count__gt=min_count),
        "metrics": Metric.objects.values("id", "unit", metric_name=F("name"))
        .annotate(readings_count=Count("readings"),
                  minimum_value=Min("readings__value"),
                  maximum_value=Max("readings__value"),
                  average_value=Avg("readings__value")).order_by("id"),
        "threshold": threshold, "message": message, "orm_data": True,
    })


@database_page
def readings(request):
    limit = request.GET.get("limit", "10").strip()
    offset = request.GET.get("offset", "0").strip()
    message = ""
    try:
        page_size, start = integer(limit, 1, 100), integer(offset, 0, 1000000)
    except ValueError:
        page_size, start = 10, 0
        message = "Размер страницы: 1–100, сдвиг: 0–1000000."
    rows = Reading.objects.values(
        "id", "report_id", "sensor_id", "measured_at", "value", "minimum",
        "maximum", "status", room_name=F("sensor__room__name"),
        metric_name=F("metric__name"), unit=F("metric__unit"),
    ).order_by("-measured_at", "id")[start:start + page_size]
    return render(request, "reports_web/readings.html", {
        "readings": rows, "metrics": Metric.objects.all().order_by("id"),
        "limit": limit, "offset": offset, "message": message,
        "orm_data": True,
    })
