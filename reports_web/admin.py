from django.contrib import admin

from .models import Metric, Reading, Report


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "unit", "minimum", "maximum")

    def get_readonly_fields(self, request, obj=None):
        return ("id",) if obj else ()


class HistoryAdmin(admin.ModelAdmin):
    """Снимки прошлых проверок доступны для чтения."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Report)
class ReportAdmin(HistoryAdmin):
    list_display = ("id", "room_name", "checked_at", "status")
    list_filter = ("status",)


@admin.register(Reading)
class ReadingAdmin(HistoryAdmin):
    list_display = ("id", "sensor_id", "metric_id", "value", "measured_at")
