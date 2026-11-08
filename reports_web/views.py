"""Исторические отчёты: только загрузка, поиск и передача контекста."""

from django.conf import settings
from django.shortcuts import render

from . import orm_views, sql_views

from homepage.views import data_unavailable
from smartspace_web.data import load_project_data


def report_list(request):
    """Сохранённый порядок и снимки Report остаются неизменными."""
    if settings.SMARTSPACE_DATA_SOURCE == "orm":
        return orm_views.report_list(request)
    if settings.SMARTSPACE_DATA_SOURCE == "sqlite":
        return sql_views.report_list(request)
    try:
        data = load_project_data()
    except (OSError, ValueError):
        return data_unavailable(request)
    context = {"reports": data.reports}
    return render(request, "reports_web/report_list.html", context)


def report_detail(request, report_id):
    """Неизвестный строковый ID даёт шаблон с сообщением и статус 404."""
    if settings.SMARTSPACE_DATA_SOURCE == "orm":
        return orm_views.report_detail(request, report_id)
    if settings.SMARTSPACE_DATA_SOURCE == "sqlite":
        return sql_views.report_detail(request, report_id)
    try:
        data = load_project_data()
    except (OSError, ValueError):
        return data_unavailable(request)
    report = next(
        (item for item in data.reports if item.id == report_id), None,
    )
    context = {"report": report}
    return render(
        request, "reports_web/report_detail.html", context,
        status=404 if report is None else 200,
    )


def statistics(request):
    if settings.SMARTSPACE_DATA_SOURCE == "orm":
        return orm_views.statistics(request)
    return sql_views.statistics(request)


def readings(request):
    if settings.SMARTSPACE_DATA_SOURCE == "orm":
        return orm_views.readings(request)
    return sql_views.readings(request)
