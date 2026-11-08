"""Помещения SmartSpace; таблицы создаются миграциями в db.sqlite3."""

from django.db import models

from smartspace_web.validators import nonblank_text, positive_number


class Room(models.Model):
    name = models.CharField("Название", max_length=200,
                            validators=[nonblank_text])
    floor = models.IntegerField("Этаж", default=0)
    area = models.FloatField("Площадь, м²", validators=[positive_number])

    class Meta:
        ordering = ["id"]
        verbose_name = "Помещение"
        verbose_name_plural = "Помещения"
        constraints = [
            models.CheckConstraint(condition=models.Q(area__gt=0),
                                   name="room_positive_area"),
            models.CheckConstraint(condition=models.Q(id__gt=0),
                                   name="room_positive_id"),
        ]

    def __str__(self):
        return f"{self.name} (этаж {self.floor})"
