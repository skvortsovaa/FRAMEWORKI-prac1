"""python manage.py import_pr7 [--source путь] [--update]."""

import sqlite3

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from db.import_sqlite_to_orm import import_source


class Command(BaseCommand):
    help = "Перенести SQLite ПР7 в базу Django, сохранив ID и связи"

    def add_arguments(self, parser):
        parser.add_argument("--source")
        parser.add_argument("--update", action="store_true")

    def handle(self, *args, **options):
        try:
            counts = import_source(options["source"], update=options["update"])
        except (OSError, ValueError, sqlite3.Error, DatabaseError,
                ValidationError) as error:
            raise CommandError(str(error)) from error
        for table, count in counts.items():
            self.stdout.write(f"{table}: {count}")
        self.stdout.write(self.style.SUCCESS("Перенос и сверка завершены."))
