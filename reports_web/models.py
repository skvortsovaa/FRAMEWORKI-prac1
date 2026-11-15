"""Показатели, исторические отчёты и измерения Django ORM."""

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator
from django.db import models

from models.metrics import analyze_metric
from models.reports import get_room_status
from smartspace_web.validators import finite_number, nonblank_text
from .querysets import ReportQuerySet


class Status(models.TextChoices):
    NORMAL = "НОРМА", "Норма"
    WARNING = "ПРЕДУПРЕЖДЕНИЕ", "Предупреждение"
    ALARM = "АВАРИЯ", "Авария"
    NO_DATA = "НЕТ ДАННЫХ", "Нет данных"


class Metric(models.Model):
    id = models.CharField(
        verbose_name='Идентификатор',
        primary_key=True,
        max_length=100,
        validators=[nonblank_text],
    )
    name = models.CharField(
        verbose_name='Название',
        max_length=200,
        validators=[nonblank_text])
    unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=30,
        validators=[nonblank_text])
    minimum = models.FloatField(
        verbose_name='Нижняя граница',
        validators=[finite_number])
    maximum = models.FloatField(
        verbose_name='Верхняя граница',
        validators=[finite_number])

    class Meta:
        ordering = ["id"]
        verbose_name = "Показатель"
        verbose_name_plural = "Показатели"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(minimum__lte=models.F("maximum")),
                name="metric_ordered_limits",
            ),
            models.CheckConstraint(
                condition=(~models.Q(id="leak")
                           | models.Q(minimum=0, maximum=0)),
                name="metric_leak_limits",
            ),
        ]

    def __str__(self):
        return f"{self.name}, {self.unit}"


class Report(models.Model):
    objects = ReportQuerySet.as_manager()

    id = models.CharField(
        verbose_name='Идентификатор',
        primary_key=True,
        max_length=100,
        validators=[nonblank_text],
    )
    room = models.ForeignKey("rooms_web.Room", verbose_name="Помещение",
                             on_delete=models.PROTECT,
                             related_name="reports")
    room_name = models.CharField(
        verbose_name='Помещение при проверке',
        max_length=200,
        validators=[nonblank_text])
    checked_at = models.DateTimeField(verbose_name='Дата и время проверки')
    sensor_active = models.BooleanField(verbose_name='Датчик был включён')
    battery = models.PositiveSmallIntegerField(
        verbose_name='Заряд при проверке, %',
        validators=[MaxValueValidator(100)],
    )
    temperature_value = models.FloatField(
        verbose_name='Температура, значение',
        null=True,
        blank=True,
        validators=[finite_number],
    )
    temperature_minimum = models.FloatField(
        verbose_name='Температура, нижняя граница',
        null=True,
        blank=True,
        validators=[finite_number],
    )
    temperature_maximum = models.FloatField(
        verbose_name='Температура, верхняя граница',
        null=True,
        blank=True,
        validators=[finite_number],
    )
    temperature_normal = models.BooleanField(
        verbose_name='Температура, в норме', null=True, blank=True)
    humidity_value = models.FloatField(
        verbose_name='Влажность, значение',
        null=True,
        blank=True,
        validators=[finite_number],
    )
    humidity_minimum = models.FloatField(
        verbose_name='Влажность, нижняя граница',
        null=True,
        blank=True,
        validators=[finite_number],
    )
    humidity_maximum = models.FloatField(
        verbose_name='Влажность, верхняя граница',
        null=True,
        blank=True,
        validators=[finite_number],
    )
    humidity_normal = models.BooleanField(
        verbose_name='Влажность, в норме', null=True, blank=True)
    leak_detected = models.BooleanField(
        verbose_name='Обнаружена протечка', null=True, blank=True)
    status = models.CharField(
        verbose_name='Статус',
        max_length=20,
        choices=Status.choices)

    class Meta:
        ordering = ["-checked_at", "id"]
        verbose_name = "Отчёт"
        verbose_name_plural = "Отчёты"
        indexes = [models.Index(fields=["room", "checked_at"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(battery__lte=100),
                                   name="report_battery_range"),
            models.CheckConstraint(
                condition=models.Q(status__in=Status.values),
                name="report_valid_status",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(sensor_active=True, battery__gt=0)
                    & ~models.Q(status=Status.NO_DATA)
                    & models.Q(**{f"{metric}_{field}__isnull": False
                                  for metric in ("temperature", "humidity")
                                  for field in ("value", "minimum", "maximum",
                                                "normal")})
                    & models.Q(leak_detected__isnull=False)
                ) | (
                    (models.Q(sensor_active=False) | models.Q(battery=0))
                    & models.Q(status=Status.NO_DATA)
                    & models.Q(**{f"{metric}_{field}__isnull": True
                                  for metric in ("temperature", "humidity")
                                  for field in ("value", "minimum", "maximum",
                                                "normal")})
                    & models.Q(leak_detected__isnull=True)
                ), name="report_snapshot_completeness",
            ),
        ]

    def _analysis(self, metric):
        if getattr(self, f"{metric}_value") is None:
            return None
        return {field: getattr(self, f"{metric}_{field}")
                for field in ("value", "minimum", "maximum", "normal")}

    @property
    def temperature(self):
        return self._analysis("temperature")

    @property
    def humidity(self):
        return self._analysis("humidity")

    def clean(self):
        super().clean()
        available = self.sensor_active and (self.battery or 0) > 0
        try:
            normal = []
            for metric in ("temperature", "humidity"):
                fields = [getattr(self, f"{metric}_{field}")
                          for field in ("value", "minimum", "maximum",
                                        "normal")]
                if available:
                    result = analyze_metric(*fields[:3])
                    if result.normal != fields[3]:
                        raise ValueError("Неверная оценка показания.")
                    normal.append(result.normal)
                elif any(value is not None for value in fields):
                    raise ValueError("У недоступного датчика нет показаний.")
            if available and self.leak_detected is None:
                raise ValueError("Не указано состояние протечки.")
            if not available and self.leak_detected is not None:
                raise ValueError("У недоступного датчика нет показаний.")
            expected = (get_room_status(True, *normal, self.leak_detected)
                        if available else Status.NO_DATA)
            if self.status != expected:
                raise ValueError("Статус не соответствует показаниям.")
        except (ValueError, TypeError) as error:
            raise ValidationError(str(error)) from error

    def __str__(self):
        return f"{self.room_name}: {self.status} ({self.id})"


class Reading(models.Model):
    id = models.CharField(
        verbose_name='Идентификатор',
        primary_key=True,
        max_length=100,
        validators=[nonblank_text],
    )
    sensor = models.ForeignKey("sensors_web.Sensor", verbose_name="Датчик",
                               on_delete=models.PROTECT,
                               related_name="readings")
    metric = models.ForeignKey(Metric, verbose_name="Показатель",
                               on_delete=models.PROTECT,
                               related_name="readings")
    report = models.ForeignKey(Report, verbose_name="Отчёт",
                               on_delete=models.PROTECT,
                               related_name="readings")
    measured_at = models.DateTimeField(
        verbose_name='Время измерения', db_index=True)
    value = models.FloatField(
        verbose_name='Значение',
        validators=[finite_number])
    minimum = models.FloatField(
        verbose_name='Нижняя граница',
        validators=[finite_number])
    maximum = models.FloatField(
        verbose_name='Верхняя граница',
        validators=[finite_number])
    status = models.CharField(verbose_name='Статус', max_length=20, choices=[
        choice for choice in Status.choices if choice[0] != Status.NO_DATA
    ])

    class Meta:
        ordering = ["-measured_at", "id"]
        verbose_name = "Измерение"
        verbose_name_plural = "Измерения"
        constraints = [
            models.UniqueConstraint(fields=["report", "metric"],
                                    name="one_reading_per_report_metric"),
            models.CheckConstraint(
                condition=models.Q(minimum__lte=models.F("maximum")),
                name="reading_ordered_limits",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=Status.values[:3]),
                name="reading_valid_status",
            ),
        ]

    def clean(self):
        super().clean()
        try:
            result = analyze_metric(self.value, self.minimum, self.maximum)
            expected = Status.NORMAL if result.normal else Status.WARNING
            if self.metric_id == "leak":
                if (self.value not in (0, 1)
                        or (self.minimum, self.maximum) != (0, 0)):
                    raise ValueError("Протечка: значение 0/1, норма 0.")
                expected = Status.ALARM if self.value else Status.NORMAL
            if self.status != expected:
                raise ValueError("Неверный статус измерения.")
            if self.sensor.room_id != self.report.room_id:
                raise ValueError("Датчик и отчёт из разных помещений.")
            if self.measured_at != self.report.checked_at:
                raise ValueError("Время измерения не совпадает с отчётом.")
            if self.metric_id == "leak":
                if self.report.leak_detected is None or (
                    self.value != int(self.report.leak_detected)
                ):
                    raise ValueError("Протечка не совпадает с отчётом.")
            elif self.metric_id in ("temperature", "humidity"):
                snapshot = getattr(self.report, self.metric_id)
                if snapshot is None or any(
                    getattr(self, key) != snapshot[key]
                    for key in ("value", "minimum", "maximum")
                ):
                    raise ValueError("Измерение не совпадает с отчётом.")
        except (ValueError, TypeError, ObjectDoesNotExist) as error:
            raise ValidationError(str(error)) from error

    def __str__(self):
        return f"{self.sensor_id}: {self.value} ({self.metric_id})"
