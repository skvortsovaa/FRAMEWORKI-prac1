"""Чтение и запись состояния проекта в JSON."""

import json
from pathlib import Path

from rooms import validate_room


def validate_data(data: dict) -> None:
    """Проверить структуру загруженных коллекций и связи записей."""
    if not isinstance(data, dict):
        raise ValueError("Корень JSON должен быть словарём.")
    if not isinstance(data.get("rooms"), list):
        raise ValueError("Поле rooms должно быть списком.")
    if not isinstance(data.get("reports"), list):
        raise ValueError("Поле reports должно быть списком.")
    room_ids = set()
    for room in data["rooms"]:
        validate_room(room)
        if room["id"] in room_ids:
            raise ValueError("Повторяется ID помещения.")
        room_ids.add(room["id"])
    for report in data["reports"]:
        if not isinstance(report, dict):
            raise ValueError("Запись истории должна быть словарём.")
        for field in ("id", "room_name", "checked_at", "status"):
            if not isinstance(report.get(field), str):
                raise ValueError(f"Некорректное поле истории: {field}.")
        room_id = report.get("room_id")
        if type(room_id) is not int or room_id not in room_ids:
            raise ValueError("История ссылается на неизвестное помещение.")


def load_data(filename: Path) -> dict:
    """Загрузить данные; отсутствие файла означает пустой проект."""
    try:
        with filename.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return {"rooms": [], "reports": []}
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError(f"Не удалось прочитать JSON: {filename}") from error
    validate_data(data)
    return data


def save_data(filename: Path, data: dict) -> None:
    """Сохранить обе коллекции, заменив файл после успешной записи."""
    validate_data(data)
    filename.parent.mkdir(parents=True, exist_ok=True)
    temporary = filename.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write("\n")
    temporary.replace(filename)
