from django.contrib import admin, messages

from .models import Sensor


class SensorInline(admin.StackedInline):
    model = Sensor
    extra = 0
    max_num = 1
    show_change_link = True

    def get_readonly_fields(self, request, obj=None):
        sensor = getattr(obj, "sensor", None)
        return ("id",) if sensor and sensor.readings.exists() else ()


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "active", "battery", "available")
    list_display_links = ("id",)
    list_editable = ("active", "battery")
    list_select_related = ("room",)
    search_fields = ("id", "room__name")
    list_filter = ("active", "room__floor")
    ordering = ("room__name", "id")
    list_per_page = 20
    autocomplete_fields = ("room",)
    actions = ("enable_sensors", "disable_sensors")

    @admin.display(boolean=True, description="Доступен")
    def available(self, obj):
        return obj.is_available()

    def get_readonly_fields(self, request, obj=None):
        # Перестановка датчика с историей нарушила бы связь старых измерений.
        return ("id", "room") if obj and obj.readings.exists() else ()

    @admin.action(description="Включить выбранные датчики",
                  permissions=["change"])
    def enable_sensors(self, request, queryset):
        count = queryset.update(active=True)
        self.message_user(request, f"Включено датчиков: {count}.",
                          messages.SUCCESS)

    @admin.action(description="Отключить выбранные датчики",
                  permissions=["change"])
    def disable_sensors(self, request, queryset):
        count = queryset.update(active=False)
        self.message_user(request, f"Отключено датчиков: {count}.",
                          messages.SUCCESS)
