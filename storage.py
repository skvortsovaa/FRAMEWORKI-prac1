"""Граница JSON и объектной модели; сохранение с резервным журналом."""

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, TypeVar

from models import Metric, ProjectData, Reading, Report, Room, Sensor
from models.metrics import MetricAnalysis
from models.readings import record_report_readings
from models.sensors import get_room_sensor
from models.validation import require_text


COLLECTIONS = ("rooms", "sensors", "metrics", "readings", "reports")
JOURNAL = ".save-backup.json"
T = TypeVar("T")


def empty_data() -> ProjectData:
    return ProjectData()


def validate_data(data: ProjectData) -> None:
    """Проверить сущности, уникальность ID и идентичность общих объектов."""
    if not isinstance(data, ProjectData):
        raise ValueError("Ожидается объект ProjectData.")
    types = (Room, Sensor, Metric, Reading, Report)
    for name, model in zip(COLLECTIONS, types):
        items = getattr(data, name)
        if not isinstance(items, list):
            raise ValueError(f"Коллекция {name} должна быть списком.")
        ids = set()
        for item in items:
            if not isinstance(item, model):
                raise ValueError(f"Неверный тип объекта в {name}.")
            item.validate()
            if item.id in ids:
                raise ValueError(f"Повторяется ID в коллекции {name}.")
            ids.add(item.id)
    rooms = {room.id: room for room in data.rooms}
    sensors = {sensor.id: sensor for sensor in data.sensors}
    metrics = {metric.id: metric for metric in data.metrics}
    reports = {report.id: report for report in data.reports}
    if set(metrics) != {"temperature", "humidity", "leak"}:
        raise ValueError("Нужны показатели temperature, humidity и leak.")
    sensor_rooms = set()
    for sensor in data.sensors:
        if rooms.get(sensor.room.id) is not sensor.room:
            raise ValueError("Датчик должен ссылаться на помещение коллекции.")
        if sensor.room.id in sensor_rooms:
            raise ValueError("У помещения может быть только один датчик.")
        sensor_rooms.add(sensor.room.id)
    if sensor_rooms != set(rooms):
        raise ValueError("У каждого помещения должен быть датчик.")
    for report in data.reports:
        if rooms.get(report.room.id) is not report.room:
            raise ValueError("История ссылается на другое помещение.")
    for reading in data.readings:
        if sensors.get(reading.sensor.id) is not reading.sensor:
            raise ValueError("Неизвестная связь измерения: sensor.")
        if metrics.get(reading.metric.id) is not reading.metric:
            raise ValueError("Неизвестная связь измерения: metric.")
        report = reports.get(reading.report_id)
        if report is None:
            raise ValueError("Неизвестная связь измерения: report_id.")
        if reading.sensor.room is not report.room:
            raise ValueError("Измерение и отчёт относятся к разным комнатам.")
        if reading.measured_at != report.checked_at:
            raise ValueError("Время измерения не соответствует отчёту.")
        if reading.metric.id == "leak":
            if (report.leak_detected is None
                    or reading.value != int(report.leak_detected)):
                raise ValueError("Протечка не совпадает с отчётом.")
        else:
            result = getattr(report, reading.metric.id)
            if result is None or (reading.value, reading.minimum,
                                  reading.maximum) != (
                    result.value, result.minimum, result.maximum):
                raise ValueError("Измерение не соответствует отчёту.")


def read_json(filename: Path) -> Any:
    """Прочитать JSON; его структуру проверяет decode_data или миграция."""
    try:
        with filename.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError(f"Не удалось прочитать JSON: {filename}") from error


def _linked(objects: dict[Any, T], key: Any) -> T:
    if type(key) not in (int, str) or key not in objects:
        raise ValueError(f"Неизвестный идентификатор связи: {key!r}.")
    return objects[key]


def _analysis(raw: Any) -> MetricAnalysis | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Анализ показателя должен быть объектом JSON.")
    return MetricAnalysis(raw["value"], raw["minimum"], raw["maximum"],
                          raw["normal"], raw["position"], raw["deviation"])


def decode_data(raw: dict[str, Any]) -> ProjectData:
    """Создать объекты; один ID соответствует одному экземпляру в памяти."""
    if not isinstance(raw, dict):
        raise ValueError("Ожидаются JSON-коллекции.")
    for name in COLLECTIONS:
        if (not isinstance(raw.get(name), list)
                or any(not isinstance(row, dict) for row in raw[name])):
            raise ValueError(f"Неверная структура коллекции {name}.")
    try:
        data = ProjectData(
            rooms=[Room(r["id"], r["name"], r["floor"], r["area"])
                   for r in raw["rooms"]],
            metrics=[Metric(m["id"], m["name"], m["unit"],
                            m["minimum"], m["maximum"])
                     for m in raw["metrics"]],
        )
        rooms = {room.id: room for room in data.rooms}
        metrics = {metric.id: metric for metric in data.metrics}
        data.sensors = [
            Sensor(s["id"], _linked(rooms, s["room_id"]),
                   s["active"], s["battery"]) for s in raw["sensors"]
        ]
        sensors = {sensor.id: sensor for sensor in data.sensors}
        data.reports = [
            Report(r["id"], _linked(rooms, r["room_id"]), r["room_name"],
                   r["checked_at"], r["sensor_active"], r["battery"],
                   _analysis(r["temperature"]), _analysis(r["humidity"]),
                   r["leak_detected"], r["status"]) for r in raw["reports"]
        ]
        for row in raw["readings"]:
            require_text(row["status"], "статус измерения")
        data.readings = [
            Reading(r["id"], _linked(sensors, r["sensor_id"]),
                    _linked(metrics, r["metric_id"]), r["value"],
                    r["report_id"], r["measured_at"], r["minimum"],
                    r["maximum"], r["status"]) for r in raw["readings"]
        ]
        validate_data(data)
        return data
    except (KeyError, TypeError) as error:
        raise ValueError("Некорректные поля в JSON-данных.") from error


def encode_data(data: ProjectData) -> dict[str, list[dict[str, Any]]]:
    """Явно записать поля прежнего формата ПР2 и ID связанных объектов."""
    validate_data(data)
    return {
        "rooms": [
            {"id": r.id, "name": r.name, "floor": r.floor, "area": r.area}
            for r in data.rooms
        ],
        "sensors": [
            {"id": s.id, "room_id": s.room.id, "active": s.active,
             "battery": s.battery} for s in data.sensors
        ],
        "metrics": [
            {"id": m.id, "name": m.name, "unit": m.unit,
             "minimum": m.minimum, "maximum": m.maximum}
            for m in data.metrics
        ],
        "readings": [
            {"id": r.id, "sensor_id": r.sensor.id, "metric_id": r.metric.id,
             "report_id": r.report_id, "measured_at": r.measured_at,
             "value": r.value, "minimum": r.minimum, "maximum": r.maximum,
             "status": r.status} for r in data.readings
        ],
        "reports": [
            {"id": r.id, "room_id": r.room.id, "room_name": r.room_name,
             "checked_at": r.checked_at, "sensor_active": r.sensor_active,
             "battery": r.battery,
             "temperature": asdict(r.temperature) if r.temperature else None,
             "humidity": asdict(r.humidity) if r.humidity else None,
             "leak_detected": r.leak_detected, "status": r.status}
            for r in data.reports
        ],
    }


def migrate_legacy(legacy: dict[str, Any]) -> ProjectData:
    """Перенести state.json; исходный файл и снимки истории не изменяются."""
    if not isinstance(legacy, dict) or any(
        not isinstance(legacy.get(key), list) for key in ("rooms", "reports")
    ):
        raise ValueError("Неверная структура старого state.json.")
    raw = encode_data(empty_data())
    for original in legacy["rooms"]:
        if not isinstance(original, dict):
            raise ValueError("Помещение должно быть объектом JSON.")
        room = deepcopy(original)
        sensor = room.pop("sensor", None)
        if not isinstance(sensor, dict) or "id" not in room:
            raise ValueError("У старого помещения должен быть датчик и ID.")
        sensor["room_id"] = room["id"]
        raw["rooms"].append(room)
        raw["sensors"].append(sensor)
    raw["reports"] = deepcopy(legacy["reports"])
    data = decode_data(raw)
    for report in data.reports:
        sensor = get_room_sensor(data.sensors, report.room.id)
        record_report_readings(data.readings, sensor, data.metrics, report)
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


def load_data(directory: Path) -> ProjectData:
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
    return decode_data(data)


def save_data(directory: Path, data: ProjectData) -> None:
    """Сохранить коллекции с откатом при ошибке или следующем запуске."""
    raw = encode_data(data)
    serialized = {
        name: json.dumps(raw[name], ensure_ascii=False, indent=2,
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
