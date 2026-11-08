from django.contrib import admin

from .models import Sensor


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "active", "battery")
    list_select_related = ("room",)
    search_fields = ("id", "room__name")
    list_filter = ("active",)

    def get_readonly_fields(self, request, obj=None):
        # Перестановка датчика с историей нарушила бы связь старых измерений.
        return ("id", "room") if obj and obj.readings.exists() else ()
