"""Чтение объектов ПР3 для веб-страниц без записи в JSON-хранилище."""

from django.conf import settings

from models import ProjectData
from storage import COLLECTIONS, JOURNAL, decode_data, read_json


def load_project_data() -> ProjectData:
    """Прочитать текущий набор JSON; восстановление остаётся в консоли."""
    directory = settings.BASE_DIR / "data"
    if (directory / JOURNAL).exists():
        raise ValueError("JSON-хранилище ожидает восстановления.")
    raw = {
        name: read_json(directory / f"{name}.json")
        for name in COLLECTIONS
    }
    try:
        return decode_data(raw)
    except OverflowError as error:
        raise ValueError("Числовые значения JSON слишком велики.") from error
