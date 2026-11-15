"""У помещения не более одного датчика; историю защищает PROTECT."""

from django.core.validators import MaxValueValidator
from django.db import models

from smartspace_web.validators import nonblank_text


class Sensor(models.Model):
    id = models.CharField("Идентификатор", primary_key=True, max_length=100,
                          validators=[nonblank_text])
    room = models.OneToOneField(
        "rooms_web.Room", on_delete=models.PROTECT,
        related_name="sensor", verbose_name="Помещение",
    )
    active = models.BooleanField("Включён", default=True)
    battery = models.PositiveSmallIntegerField(
        "Заряд, %", default=100, validators=[MaxValueValidator(100)],
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Датчик"
        verbose_name_plural = "Датчики"
        constraints = [models.CheckConstraint(
            condition=models.Q(battery__lte=100), name="sensor_battery_range",
        )]

    def is_available(self):
        return self.active and self.battery > 0

    def __str__(self):
        return f"{self.id} (помещение {self.room_id})"
