"""Создать учебную группу наблюдателей без выдачи прав изменения данных."""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Создать группу «Наблюдатели SmartSpace» с правами просмотра."

    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name="Наблюдатели SmartSpace")
        permissions = Permission.objects.filter(
            content_type__app_label__in=(
                "rooms_web", "sensors_web", "reports_web",
            ), codename__startswith="view_",
        )
        group.permissions.set(permissions)
        self.stdout.write(self.style.SUCCESS(
            f"{group.name}: {permissions.count()} разрешений просмотра. "
            "Пользователей команда не создаёт и is_staff не меняет."
        ))
