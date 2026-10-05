"""Консольное меню SmartSpace Monitor и вывод результатов."""

from copy import deepcopy
from pathlib import Path

from monitoring import check_room
from models.metrics import MetricAnalysis, get_metric
from models.readings import find_readings
from models.rooms import (
    Room, add_room, find_rooms, get_room, iter_rooms_on_floor,
    sort_rooms,
)
from models.sensors import Sensor, add_sensor, get_room_sensor
from models.reports import Report
from models.state import ProjectData
from storage import load_data, save_data
from utils import input_float, input_int


DATA_DIR = Path(__file__).resolve().parent / "data"
MENU = """
SMARTSPACE MONITOR — учебная симуляция
1. Показать помещения
2. Добавить помещение
3. Найти по названию
4. Показать помещения по площади
5. Показать помещения на этаже
6. Изменить состояние датчика
7. Проверить одно помещение (сценарий ПР1)
8. Проверить все помещения
9. Показать историю проверок
10. Показать датчики
11. Показать показатели и нормы
12. Изменить границы нормы показателя
13. Показать измерения датчика помещения
0. Выход
"""
RECOMMENDATIONS = {
    "НЕТ ДАННЫХ": "Восстановите работу датчика и повторите проверку.",
    "АВАРИЯ": "Протечка: немедленно сообщите службе эксплуатации.",
    "ПРЕДУПРЕЖДЕНИЕ": "Есть отклонения микроклимата. Проверьте параметры.",
    "НОРМА": "Показатели помещения в норме.",
}
METRIC_ADVICE = {
    "Температура": {
        "below": "Проверьте настройки отопления и охлаждения.",
        "above": "Проверьте вентиляцию и кондиционирование.",
    },
    "Влажность": {
        "below": "Проверьте систему увлажнения воздуха.",
        "above": "Проверьте вентиляцию и источники избыточной влаги.",
    },
}


def show_rooms(rooms: list[Room], sensors: list[Sensor]) -> None:
    """Вывести сведения о выбранных помещениях и датчиках."""
    if not rooms:
        print("Помещений не найдено.")
    for room in rooms:
        sensor = get_room_sensor(sensors, room.id)
        print(f"{room} | {sensor}")


def show_metric(name: str, result: MetricAnalysis, unit: str) -> None:
    """Вывести уже рассчитанный анализ показателя."""
    print(
        f"{name}: {result.value:.2f}{unit}; "
        f"норма {result.minimum}–{result.maximum}{unit}"
    )
    position = result.position
    if result.normal:
        print("В норме. Коррекция не требуется.")
        if name == "Температура":
            print(
                "Отклонение от середины диапазона: "
                f"{result.deviation:.2f}{unit}."
            )
    else:
        direction = "НИЖЕ" if position == "below" else "ВЫШЕ"
        deviation_unit = " п.п." if name == "Влажность" else unit
        print(
            f"{direction} нормы на "
            f"{result.deviation:.2f}{deviation_unit}."
        )
        print("Рекомендация:", METRIC_ADVICE[name][position])


def show_report(report: Report) -> None:
    """Показать подробный результат новой проверки."""
    print("\n" + "=" * 60)
    print(f"{report.room_name} | {report.checked_at}")
    print(f"ID отчёта: {report.id}")
    if report.temperature is None:
        print("Измерения недоступны: датчик отключён или батарея разряжена.")
    else:
        show_metric("Температура", report.temperature, " °C")
        show_metric("Влажность", report.humidity, "%")
        leak = "ОБНАРУЖЕНА" if report.leak_detected else "не обнаружена"
        print("Протечка:", leak)
    print("Статус помещения:", report.status)
    print("Рекомендация:", RECOMMENDATIONS[report.status])
    if not report.sensor_active:
        print("Обслуживание: проверьте подключение датчика.")
    if report.battery < 20:
        print("Обслуживание: замените или зарядите батарею датчика.")
    print("=" * 60)


def show_history(reports: list[Report]) -> None:
    """Вывести сохранённую историю, начиная с последней проверки."""
    if not reports:
        print("История проверок пуста.")
    for report in reversed(reports):
        print(report)


def perform_action(choice: str, data: ProjectData) -> bool:
    """Выполнить действие меню; вернуть, требуется ли сохранение."""
    rooms = data.rooms
    sensors = data.sensors
    if choice == "1":
        show_rooms(rooms, sensors)
    elif choice == "2":
        name = input("Название помещения: ")
        floor = input_int("Этаж: ")
        area = input_float("Площадь, кв.м: ")
        room = add_room(rooms, name, floor, area)
        add_sensor(sensors, rooms, room.id)
        return True
    elif choice == "3":
        show_rooms(find_rooms(rooms, input("Часть названия: ")), sensors)
    elif choice == "4":
        show_rooms(sort_rooms(rooms), sensors)
    elif choice == "5":
        floor = input_int("Этаж: ")
        show_rooms(list(iter_rooms_on_floor(rooms, floor)), sensors)
    elif choice == "6":
        room = get_room(rooms, input_int("ID помещения: "))
        active = input_int("Датчик активен? 1 — да, 0 — нет: ")
        if active not in (0, 1):
            raise ValueError("Для активности введите 0 или 1.")
        battery = input_int("Заряд батареи, %: ")
        sensor = get_room_sensor(sensors, room.id)
        sensor.update_state(bool(active), battery)
        return True
    elif choice in ("7", "8"):
        if choice == "7":
            selected = [get_room(rooms, input_int("ID помещения: "))]
        else:
            selected = rooms
        if not selected:
            print("Сначала добавьте помещение.")
            return False
        for room in selected:
            sensor = get_room_sensor(sensors, room.id)
            report = check_room(
                room, sensor, data.metrics, data.readings,
            )
            data.reports.append(report)
            show_report(report)
        return True
    elif choice == "9":
        show_history(data.reports)
    elif choice == "10":
        if not sensors:
            print("Датчиков пока нет.")
        for sensor in sensors:
            print(sensor)
    elif choice == "11":
        for metric in data.metrics:
            print(metric)
    elif choice == "12":
        metric = get_metric(data.metrics, input("ID показателя: ").strip())
        if metric.id == "leak":
            raise ValueError("Норма протечки фиксирована: 0 (нет протечки).")
        minimum = input_float("Нижняя граница: ")
        maximum = input_float("Верхняя граница: ")
        metric.update_limits(minimum, maximum)
        return True
    elif choice == "13":
        room = get_room(rooms, input_int("ID помещения: "))
        sensor = get_room_sensor(sensors, room.id)
        readings = find_readings(data.readings, sensor.id)
        if not readings:
            print("Измерений пока нет. Выполните проверку помещения.")
        for reading in readings:
            print(reading)
    else:
        print("Нет такого пункта меню.")
    return False


def main() -> None:
    """Загрузить данные и обрабатывать команды до выхода."""
    try:
        data = load_data(DATA_DIR)
    except (OSError, ValueError) as error:
        print(f"Ошибка загрузки: {error}")
        print("Исправьте файл данных и запустите программу снова.")
        return
    while True:
        try:
            print(MENU)
            choice = input("Выберите действие: ").strip()
            if choice == "0":
                print("До свидания!")
                break
            # Копия защищает текущее состояние при ошибке записи.
            candidate = deepcopy(data)
            if perform_action(choice, candidate):
                save_data(DATA_DIR, candidate)
                data = candidate
                print("Изменения сохранены.")
        except (ValueError, OSError) as error:
            print(f"Действие не сохранено: {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nРабота завершена.")
            break


if __name__ == "__main__":
    main()
