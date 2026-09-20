import datetime
import random

room_name = "Серверная №1"
room_floor = 3
room_area = 25.5
sensor_id = "SENS-001"
sensor_active = True
sensor_battery_level = 85

# Демонстрационные пороги температуры (°C) и влажности (%).
metric_min_normal = 18.0
metric_max_normal = 24.0
humidity_min_normal = 40.0
humidity_max_normal = 60.0


def validate_settings(area, battery, temperature_min, temperature_max, humidity_min, humidity_max):
    if area <= 0:
        raise SystemExit("Ошибка: площадь помещения должна быть больше нуля.")
    if not 0 <= battery <= 100:
        raise SystemExit("Ошибка: заряд батареи должен быть от 0 до 100%.")
    if temperature_min > temperature_max:
        raise SystemExit("Ошибка: минимум температуры больше максимума.")
    if not 0 <= humidity_min <= humidity_max <= 100:
        raise SystemExit("Ошибка: границы влажности должны быть упорядочены и лежать в пределах 0–100%.")


def print_room_info(name, floor, area, check_time):
    print("=" * 60)
    print("SMARTSPACE MONITOR — Система мониторинга помещений")
    print("=" * 60)
    print("Учебная симуляция. Пороги заданы для примера.")
    print(f"Время проверки: {check_time.strftime('%d.%m.%Y %H:%M:%S')}")
    print()
    print("ИНФОРМАЦИЯ О ПОМЕЩЕНИИ:")
    print(f"   Название: {name}")
    print(f"   Этаж: {floor}")
    print(f"   Площадь: {area} кв.м")


def check_sensor(identifier, active, battery):
    print()
    print("ИНФОРМАЦИЯ О ДАТЧИКЕ:")
    print(f"   ID датчика: {identifier}")
    print(f"   Статус: {'Активен' if active else 'Неактивен'}")
    print(f"   Заряд батареи: {battery}%")
    if not active:
        print("   ВНИМАНИЕ: датчик неактивен. Проверьте подключение.")
    if battery == 0:
        print("   ВНИМАНИЕ: батарея разряжена. Измерения недоступны.")
    elif battery < 20:
        print("   ВНИМАНИЕ: низкий заряд. Замените или зарядите батарею.")
    elif active:
        print("   Датчик работает нормально.")
    return active and battery > 0


def analyze_temperature(value, minimum, maximum):
    print(f"   Температура: {value:.2f} °C")
    print(f"   Норма температуры: {minimum}–{maximum} °C")
    if value < minimum:
        deviation = minimum - value
        print(f"   Температура НИЖЕ нормы на {deviation:.2f} °C.")
        print("   Рекомендация: проверьте настройки отопления и охлаждения.")
        return False
    elif value > maximum:
        deviation = value - maximum
        print(f"   Температура ВЫШЕ нормы на {deviation:.2f} °C.")
        print("   Рекомендация: проверьте вентиляцию и кондиционирование.")
        return False
    else:
        normal_middle = (minimum + maximum) / 2
        deviation = abs(value - normal_middle)
        print("   Температура в норме. Коррекция не требуется.")
        print(f"   Отклонение от середины диапазона: {deviation:.2f} °C.")
        return True


def analyze_humidity(value, minimum, maximum):
    print()
    print(f"   Влажность: {value:.2f}%")
    print(f"   Норма влажности: {minimum}–{maximum}%")
    if value < minimum:
        deviation = minimum - value
        print(f"   Влажность НИЖЕ нормы на {deviation:.2f} процентного пункта.")
        print("   Рекомендация: проверьте систему увлажнения воздуха.")
        return False
    elif value > maximum:
        deviation = value - maximum
        print(f"   Влажность ВЫШЕ нормы на {deviation:.2f} процентного пункта.")
        print("   Рекомендация: проверьте вентиляцию и источники избыточной влаги.")
        return False
    else:
        print("   Влажность в норме. Коррекция не требуется.")
        return True


def get_room_status(available, temperature_normal, humidity_normal, leak_detected):
    if not available:
        return "НЕТ ДАННЫХ"
    elif leak_detected:
        return "АВАРИЯ"
    elif not temperature_normal or not humidity_normal:
        return "ПРЕДУПРЕЖДЕНИЕ"
    else:
        return "НОРМА"


def print_report(report_id, status, active, battery):
    print()
    print("=" * 60)
    print("ИТОГОВЫЙ ОТЧЁТ")
    print("=" * 60)
    print(f"ID отчёта: {report_id}")
    print(f"Статус помещения: {status}")
    if status == "НЕТ ДАННЫХ":
        recommendation = "Восстановите работу датчика и повторите проверку помещения."
    elif status == "АВАРИЯ":
        recommendation = "Обнаружена протечка: немедленно сообщите службе эксплуатации."
    elif status == "ПРЕДУПРЕЖДЕНИЕ":
        recommendation = "Есть отклонения микроклимата. Проверьте указанные параметры."
    else:
        recommendation = "Показатели помещения в норме."
    print(f"Рекомендация: {recommendation}")
    if not active:
        print("Обслуживание: проверьте подключение датчика.")
    if battery < 20:
        print("Обслуживание: замените или зарядите батарею датчика.")
    print("=" * 60)


def main():
    validate_settings(
        room_area, sensor_battery_level, metric_min_normal, metric_max_normal,
        humidity_min_normal, humidity_max_normal,
    )
    current_time = datetime.datetime.now()
    report_id = "REP-" + str(current_time.year) + "-" + str(random.randint(1000, 9999))
    print_room_info(room_name, room_floor, room_area, current_time)
    sensor_available = check_sensor(sensor_id, sensor_active, sensor_battery_level)

    temperature_normal = False
    humidity_normal = False
    leak_detected = False
    print()
    print("ПОКАЗАНИЯ И АНАЛИЗ:")
    if sensor_available:
        # Округляем до анализа, чтобы показанное значение соответствовало статусу.
        current_temperature = round(random.uniform(16.0, 28.0), 2)
        current_humidity = round(random.uniform(30.0, 75.0), 2)
        leak_detected = random.randint(1, 10) == 1
        temperature_normal = analyze_temperature(
            current_temperature, metric_min_normal, metric_max_normal,
        )
        humidity_normal = analyze_humidity(
            current_humidity, humidity_min_normal, humidity_max_normal,
        )
        print()
        print(f"   Протечка: {'ОБНАРУЖЕНА' if leak_detected else 'не обнаружена'}")
    else:
        print("   Измерения не получены: датчик отключён или батарея разряжена.")

    status = get_room_status(sensor_available, temperature_normal, humidity_normal, leak_detected)
    print_report(report_id, status, sensor_active, sensor_battery_level)


if __name__ == "__main__":
    main()
