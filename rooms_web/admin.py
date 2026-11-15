from django.contrib import admin
from django.db.models import Count

from reports_web.admin import ReportInline
from sensors_web.admin import SensorInline
from .models import Room


admin.site.site_header = "SmartSpace Monitor — управление"
admin.site.site_title = "SmartSpace Monitor"
admin.site.index_title = "Администрирование мониторинга"


class LargeRoomFilter(admin.SimpleListFilter):
    title = "Большое помещение"
    parameter_name = "large"

    def lookups(self, request, model_admin):
        return (("1", "Да"), ("0", "Нет"))

    def queryset(self, request, queryset):
        if self.value() in ("0", "1"):
            return queryset.filter(is_large=self.value() == "1")
        return queryset


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "floor", "area", "large_room", "reports_count",
    )
    list_display_links = ("id", "name")
    list_editable = ("area",)
    search_fields = ("name",)
    list_filter = ("floor", LargeRoomFilter)
    ordering = ("name", "id")
    list_per_page = 20
    readonly_fields = ("slug", "large_room")
    fields = ("name", "floor", "area", "slug", "large_room")
    inlines = (SensorInline, ReportInline)
    view_on_site = True

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            history_count=Count("reports"),
        )

    @admin.display(description="Проверок", ordering="history_count")
    def reports_count(self, obj):
        return obj.history_count

    @admin.display(description="Большое помещение", boolean=True,
                   ordering="is_large")
    def large_room(self, obj):
        return obj.is_large if obj.pk else None
