"""Общие данные навигации с одним отложенным COUNT для ORM-страниц."""

from django.conf import settings
from django.db import DatabaseError
from django.utils.functional import SimpleLazyObject

from rooms_web.models import Room


def room_context(request):
    def count_rooms():
        if settings.SMARTSPACE_DATA_SOURCE != "orm":
            return None
        try:
            return Room.objects.count()
        except DatabaseError:
            # Страница ошибки БД тоже использует базовый шаблон.
            return None

    return {"site_name": "SmartSpace Monitor",
            "navigation_rooms_count": SimpleLazyObject(count_rooms)}
