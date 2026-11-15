"""Помещения SmartSpace; таблицы создаются миграциями в db.sqlite3."""

from uuid import uuid4

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from unidecode import unidecode

from smartspace_web.validators import nonblank_text, positive_number


class Room(models.Model):
    name = models.CharField("Название", max_length=200,
                            validators=[nonblank_text])
    floor = models.IntegerField("Этаж", default=0)
    area = models.FloatField(
        "Площадь, м²", validators=[positive_number],
        help_text=("Положительная площадь в м². "
                   "Большим считается помещение от 50 м²."),
    )
    slug = models.SlugField("Адрес", max_length=220, unique=True,
                            blank=True, editable=False)
    is_large = models.GeneratedField(
        verbose_name="Большое помещение",
        expression=models.Case(
            models.When(area__gte=50, then=models.Value(True)),
            default=models.Value(False), output_field=models.BooleanField(),
        ),
        output_field=models.BooleanField(), db_persist=True,
    )

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

    def save(self, *args, **kwargs):
        # Адрес не меняется при переименовании; суффикс различает одинаковые
        # имена.
        if not self.slug:
            base = slugify(unidecode(self.name))[:160] or "room"
            self.slug = f"{base}-{uuid4().hex}"
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = set(
                    kwargs["update_fields"]) | {"slug"}
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("rooms:detail-slug", kwargs={"slug": self.slug})
