"""Отдельные JSON-коллекции, проверка связей и перенос старых данных."""

from copy import deepcopy
import json
from pathlib import Path

from models.metrics import default_metrics, validate_metric
from models.readings import record_report_readings, validate_reading
from models.rooms import validate_room
from models.sensors import get_room_sensor, validate_sensor


COLLECTIONS = ("rooms", "sensors", "metrics", "readings", "reports")
JOURNAL = ".save-backup.json"


def empty_data() -> dict:
    """Создать пустой проект с тремя поддерживаемыми показателями."""
    return {"rooms": [], "sensors": [], "metrics": default_metrics(),
            "readings": [], "reports": []}


def validate_data(data: dict) -> None:
    """Проверить коллекции, уникальность ID и внешние ключи."""
    if not isinstance(data, dict):
        raise ValueError("Корень данных должен быть словарём.")
    validators = {
        "rooms": validate_room, "sensors": validate_sensor,
        "metrics": validate_metric, "readings": validate_reading,
    }
    ids = {}
    for collection in COLLECTIONS:
        if not isinstance(data.get(collection), list):
            raise ValueError(f"Поле {collection} должно быть списком.")
        ids[collection] = set()
        for item in data[collection]:
            if collection in validators:
                validators[collection](item)
            else:
                if not isinstance(item, dict):
                    raise ValueError("Запись истории должна быть словарём.")
                for field in ("id", "room_name", "checked_at", "status"):
                    value = item.get(field)
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(
                            f"Некорректное поле истории: {field}.",
                        )
            if item["id"] in ids[collection]:
                raise ValueError(f"Повторяется ID в коллекции {collection}.")
            ids[collection].add(item["id"])
    if ids["metrics"] != {"temperature", "humidity", "leak"}:
        raise ValueError("Нужны показатели temperature, humidity и leak.")
    sensor_rooms = set()
    for sensor in data["sensors"]:
        if sensor["room_id"] not in ids["rooms"]:
            raise ValueError("Датчик ссылается на неизвестное помещение.")
        if sensor["room_id"] in sensor_rooms:
            raise ValueError("У помещения может быть только один датчик.")
        sensor_rooms.add(sensor["room_id"])
    if sensor_rooms != ids["rooms"]:
        raise ValueError("У каждого помещения должен быть датчик.")
    for report in data["reports"]:
        room_id = report.get("room_id")
        if type(room_id) is not int or room_id not in ids["rooms"]:
            raise ValueError("История ссылается на неизвестное помещение.")
    sensors = {item["id"]: item for item in data["sensors"]}
    reports = {item["id"]: item for item in data["reports"]}
    for reading in data["readings"]:
        for field, collection in (("sensor_id", "sensors"),
                                  ("metric_id", "metrics"),
                                  ("report_id", "reports")):
            if reading[field] not in ids[collection]:
                raise ValueError(f"Неизвестная связь измерения: {field}.")
        sensor = sensors[reading["sensor_id"]]
        report = reports[reading["report_id"]]
        if sensor["room_id"] != report["room_id"]:
            raise ValueError("Измерение и отчёт относятся к разным комнатам.")


def read_json(filename: Path):
    """Прочитать JSON, представляя ошибки формата как ValueError."""
    try:
        with filename.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError(f"Не удалось прочитать JSON: {filename}") from error


def migrate_legacy(legacy: dict) -> dict:
    """Разделить старое состояние, не меняя исходный словарь и отчёты."""
    if not isinstance(legacy, dict) or any(
        not isinstance(legacy.get(key), list) for key in ("rooms", "reports")
    ):
        raise ValueError("Неверная структура старого state.json.")
    data = empty_data()
    for original in legacy["rooms"]:
        if not isinstance(original, dict):
            raise ValueError("Помещение должно быть словарём.")
        room = deepcopy(original)
        sensor = room.pop("sensor", None)
        validate_room(room)
        if not isinstance(sensor, dict):
            raise ValueError("У старого помещения должен быть датчик.")
        sensor["room_id"] = room["id"]
        data["rooms"].append(room)
        data["sensors"].append(sensor)
    data["reports"] = deepcopy(legacy["reports"])
    validate_data(data)
    try:
        for report in data["reports"]:
            sensor = get_room_sensor(data["sensors"], report["room_id"])
            record_report_readings(
                data["readings"], sensor, data["metrics"], report,
            )
    except (KeyError, TypeError) as error:
        raise ValueError("Некорректные показания в старой истории.") from error
    validate_data(data)
    return data


def recover_save(directory: Path) -> None:
    """Откатить незавершённую запись по резервному журналу."""
    journal = directory / JOURNAL
    if not journal.exists():
        return
    backup = read_json(journal)
    expected = {f"{name}.json" for name in COLLECTIONS}
    if not isinstance(backup, dict) or set(backup) != expected:
        raise ValueError("Повреждён резервный журнал сохранения.")
    if any(value is not None and not isinstance(value, str)
           for value in backup.values()):
        raise ValueError("Повреждено содержимое резервного журнала.")
    for name, content in backup.items():
        filename = directory / name
        if content is None:
            filename.unlink(missing_ok=True)
        else:
            temporary = filename.with_suffix(".tmp")
            temporary.write_text(content, encoding="utf-8", newline="")
            temporary.replace(filename)
    journal.unlink()


def load_data(directory: Path) -> dict:
    """Загрузить отдельные файлы; при их отсутствии прочитать state.json."""
    recover_save(directory)
    present = [(directory / f"{name}.json").exists() for name in COLLECTIONS]
    if not any(present):
        legacy = directory / "state.json"
        return migrate_legacy(read_json(legacy)) if legacy.exists() else (
            empty_data()
        )
    if not all(present):
        raise ValueError("Неполный набор JSON-файлов в папке данных.")
    data = {name: read_json(directory / f"{name}.json")
            for name in COLLECTIONS}
    validate_data(data)
    return data


def save_data(directory: Path, data: dict) -> None:
    """Сохранить коллекции с откатом при ошибке или следующем запуске."""
    validate_data(data)
    serialized = {
        name: json.dumps(data[name], ensure_ascii=False, indent=2,
                         allow_nan=False) + "\n" for name in COLLECTIONS
    }
    directory.mkdir(parents=True, exist_ok=True)
    recover_save(directory)
    backup = {}
    for name in COLLECTIONS:
        filename = directory / f"{name}.json"
        backup[filename.name] = (
            filename.read_bytes().decode("utf-8") if filename.exists()
            else None
        )
        filename.with_suffix(".tmp").write_text(
            serialized[name], encoding="utf-8", newline="",
        )
    journal = directory / JOURNAL
    staged_journal = journal.with_suffix(".tmp")
    staged_journal.write_text(
        json.dumps(backup, ensure_ascii=False), encoding="utf-8",
    )
    staged_journal.replace(journal)
    try:
        for name in COLLECTIONS:
            filename = directory / f"{name}.json"
            filename.with_suffix(".tmp").replace(filename)
        journal.unlink()
    except OSError:
        recover_save(directory)
        raise
