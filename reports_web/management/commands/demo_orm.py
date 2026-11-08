"""CRUD для защиты ПР9, без сохранения учебных изменений."""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.deletion import ProtectedError

from rooms_web.models import Room
from sensors_web.models import Sensor


class Command(BaseCommand):
    help = "Показать create/get/save/delete и PROTECT с итоговым rollback"

    @transaction.atomic
    def handle(self, *args, **options):
        from uuid import uuid4

        room = Room.objects.create(name="Демонстрация CRUD", floor=1, area=20)
        self.stdout.write(f"CREATE: {room.pk}, {room.name}")
        room = Room.objects.get(pk=room.pk)
        room.area = 25
        room.full_clean()
        room.save(update_fields=["area"])
        room.refresh_from_db()
        self.stdout.write(f"READ / UPDATE: площадь = {room.area}")
        sensor = Sensor.objects.create(id=f"DEMO-{uuid4().hex}", room=room)
        try:
            room.delete()
        except ProtectedError:
            self.stdout.write("PROTECT: помещение с датчиком защищено")
        sensor.delete()
        room.delete()
        self.stdout.write("DELETE: учебные датчик и помещение удалены")
        transaction.set_rollback(True)
        self.stdout.write("ROLLBACK: исходные данные остались без изменений")
