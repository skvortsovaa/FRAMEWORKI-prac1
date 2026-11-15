"""Воспроизводимое чтение SQL без изменения рабочих записей."""

import json

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Count, F
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext

from reports_web.models import Reading, Report
from rooms_web.models import Room


class Command(BaseCommand):
    help = "Измерить запросы страниц, JOIN и prefetch без изменения данных."

    def handle(self, *args, **options):
        results = {"pages": {}, "comparisons": {}}
        room = Room.objects.first()
        report = Report.objects.first()
        urls = ["/", "/rooms/", "/sensors/", "/reports/",
                "/reports/?sort=room&page_size=1&page=2",
                "/reports/?exclude_no_data=1", "/reports/statistics/",
                "/reports/readings/"]
        if room:
            urls.append(room.get_absolute_url())
        if report:
            urls.append(f"/reports/{report.pk}/")
        with override_settings(ALLOWED_HOSTS=["testserver"], DEBUG=False):
            client = Client()
            for url in urls:
                with CaptureQueriesContext(connection) as queries:
                    response = client.get(url)
                results["pages"][url] = {
                    "status": response.status_code, "count": len(queries),
                    "sql": [q["sql"] for q in queries],
                }
        for label, queryset in (
            ("report_plain", Report.objects.all()[:20]),
            ("report_join", Report.objects.select_related("room")[:20]),
        ):
            with CaptureQueriesContext(connection) as queries:
                names = [r.room.name for r in queryset]
            results["comparisons"][label] = {
                "rows": len(names), "count": len(queries),
            }
        for label, queryset in (
            ("rooms_plain", Room.objects.all()[:20]),
            ("rooms_prefetch", Room.objects.prefetch_related("reports")[:20]),
        ):
            with CaptureQueriesContext(connection) as queries:
                history = [list(r.reports.all()) for r in queryset]
            results["comparisons"][label] = {
                "rooms": len(history), "count": len(queries),
            }
        projection = Reading.objects.annotate(
            metric_title=F("metric__name"),
        ).values("id", "value", "metric_title")
        results["projection_sql"] = str(projection.query)
        results["group_sql"] = str(Room.objects.annotate(
            history_count=Count("reports"),
        ).query)
        results["plan"] = Report.objects.select_related("room").explain()
        self.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))
