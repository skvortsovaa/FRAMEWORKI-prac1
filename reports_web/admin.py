from django.contrib import admin

from .models import Metric, Reading, Report


class HistoryPermissions:
    """Снимки проверок нельзя переписывать даже суперпользователю."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReportInline(HistoryPermissions, admin.TabularInline):
    model = Report
    extra = 0
    fields = ("id", "checked_at", "room_name", "status")
    readonly_fields = fields
    show_change_link = True
    ordering = ("-checked_at", "id")


class ReadingInline(HistoryPermissions, admin.TabularInline):
    model = Reading
    extra = 0
    fields = ("id", "sensor", "metric", "value", "status")
    readonly_fields = fields
    show_change_link = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("sensor", "metric")


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "unit", "minimum", "maximum")
    list_display_links = ("id", "name")
    search_fields = ("id", "name")
    ordering = ("name", "id")
    list_per_page = 20

    def get_readonly_fields(self, request, obj=None):
        return ("id",) if obj else ()


class HistoryAdmin(HistoryPermissions, admin.ModelAdmin):
    """Снимки прошлых проверок доступны для чтения."""

    list_per_page = 20


@admin.register(Report)
class ReportAdmin(HistoryAdmin):
    list_display = ("id", "room_name", "room", "checked_at", "status")
    list_select_related = ("room",)
    search_fields = ("id", "room_name", "room__name")
    list_filter = ("status", "checked_at", "room")
    ordering = ("-checked_at", "id")
    date_hierarchy = "checked_at"
    inlines = (ReadingInline,)


@admin.register(Reading)
class ReadingAdmin(HistoryAdmin):
    list_display = ("id", "sensor", "metric", "value", "measured_at", "status")
    list_select_related = ("sensor", "metric", "report")
    search_fields = ("id", "sensor__id", "sensor__room__name", "metric__name")
    list_filter = ("status", "metric", "measured_at")
    ordering = ("-measured_at", "id")
    date_hierarchy = "measured_at"
