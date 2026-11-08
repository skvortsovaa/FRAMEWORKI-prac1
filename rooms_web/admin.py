from django.contrib import admin

from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "floor", "area")
    search_fields = ("name",)
    list_filter = ("floor",)
