"""Выборки исторических проверок без скрытой фильтрации."""

from django.db import models


class ReportQuerySet(models.QuerySet):
    def normal(self):
        from .models import Status
        return self.filter(status=Status.NORMAL)

    def warnings(self):
        from .models import Status
        return self.filter(status=Status.WARNING)

    def alarms(self):
        from .models import Status
        return self.filter(status=Status.ALARM)

    def no_data(self):
        from .models import Status
        return self.filter(status=Status.NO_DATA)

    def with_data(self):
        from .models import Status
        return self.exclude(status=Status.NO_DATA)

    def for_date(self, day):
        return self.filter(checked_at__date=day)

    def for_room(self, room):
        return self.filter(room=room)
