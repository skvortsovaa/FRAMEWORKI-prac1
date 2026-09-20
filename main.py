# SmartSpace Monitor — начальная версия для ПР1.
# Один сценарий: проверка помещения и вывод отчёта.
# Используются простые типы, операции, преобразования типов и ветвления.

import datetime
import random

# ПОМЕЩЕНИЕ
room_name = "Серверная №1"     # str
room_floor = 3                 # int
room_area = 25.5               # float

# ДАТЧИК: учебная модель комбинированного устройства.
sensor_id = "SENS-001"
sensor_active = True           # bool
sensor_battery_level = 85      # процент заряда: от 0 до 100

# ПОКАЗАТЕЛИ: демонстрационные пороги, а не нормативы для всех помещений.
metric_min_normal = 18.0       # температура, °C
metric_max_normal = 24.0
humidity_min_normal = 40.0     # влажность, %
humidity_max_normal = 60.0

# Проверяем настройки до получения данных.
if room_area <= 0:
    raise SystemExit("Ошибка: площадь помещения должна быть больше нуля.")
if sensor_battery_level < 0 or sensor_battery_level > 100:
    raise SystemExit("Ошибка: заряд батареи должен быть от 0 до 100%.")
if metric_min_normal > metric_max_normal:
    raise SystemExit("Ошибка: минимум температуры больше максимума.")
if not 0 <= humidity_min_normal <= humidity_max_normal <= 100:
    raise SystemExit("Ошибка: границы влажности должны быть упорядочены и лежать в пределах 0–100%.")

current_time = datetime.datetime.now()
# Явное преобразование int в str и конкатенация строк.
report_id = "REP-" + str(current_time.year) + "-" + str(random.randint(1000, 9999))
sensor_available = sensor_active and sensor_battery_level > 0

print("=" * 60)
print("SMARTSPACE MONITOR — Система мониторинга помещений")
print("=" * 60)
print("Учебная симуляция. Пороги заданы для примера.")
print(f"Время проверки: {current_time.strftime('%d.%m.%Y %H:%M:%S')}")
print()
print("ИНФОРМАЦИЯ О ПОМЕЩЕНИИ:")
print(f"   Название: {room_name}")
print(f"   Этаж: {room_floor}")
print(f"   Площадь: {room_area} кв.м")
print()
print("ИНФОРМАЦИЯ О ДАТЧИКЕ:")
print(f"   ID датчика: {sensor_id}")
print(f"   Статус: {'Активен' if sensor_active else 'Неактивен'}")
print(f"   Заряд батареи: {sensor_battery_level}%")

# Независимые проверки: отключение и проблемы питания могут совпадать.
if not sensor_active:
    print("   ВНИМАНИЕ: датчик неактивен. Проверьте подключение.")
if sensor_battery_level == 0:
    print("   ВНИМАНИЕ: батарея разряжена. Измерения недоступны.")
elif sensor_battery_level < 20:
    print("   ВНИМАНИЕ: низкий заряд. Замените или зарядите батарею.")
elif sensor_active:
    print("   Датчик работает нормально.")

print()
print("ПОКАЗАНИЯ И АНАЛИЗ:")
if sensor_available:
    # Округляем ДО анализа: отображаемое значение соответствует статусу.
    current_temperature = round(random.uniform(16.0, 28.0), 2)
    current_humidity = round(random.uniform(30.0, 75.0), 2)
    leak_detected = random.randint(1, 10) == 1   # bool, вероятность 10%

    print(f"   Температура: {current_temperature:.2f} °C")
    print(f"   Норма температуры: {metric_min_normal}–{metric_max_normal} °C")
    if current_temperature < metric_min_normal:
        temperature_deviation = metric_min_normal - current_temperature
        temperature_normal = False
        temperature_recommendation = "Проверьте настройки отопления и охлаждения."
        print(f"   Температура НИЖЕ нормы на {temperature_deviation:.2f} °C.")
    elif current_temperature > metric_max_normal:
        temperature_deviation = current_temperature - metric_max_normal
        temperature_normal = False
        temperature_recommendation = "Проверьте вентиляцию и кондиционирование."
        print(f"   Температура ВЫШЕ нормы на {temperature_deviation:.2f} °C.")
    else:
        temperature_normal = True
        temperature_recommendation = "Коррекция температуры не требуется."
        normal_middle = (metric_min_normal + metric_max_normal) / 2
        deviation_from_middle = abs(current_temperature - normal_middle)
        print("   Температура в норме.")
        print(f"   Отклонение от середины диапазона: {deviation_from_middle:.2f} °C.")

    print()
    print(f"   Влажность: {current_humidity:.2f}%")
    print(f"   Норма влажности: {humidity_min_normal}–{humidity_max_normal}%")
    if current_humidity < humidity_min_normal:
        humidity_deviation = humidity_min_normal - current_humidity
        humidity_normal = False
        humidity_recommendation = "Проверьте систему увлажнения воздуха."
        print(f"   Влажность НИЖЕ нормы на {humidity_deviation:.2f} процентного пункта.")
    elif current_humidity > humidity_max_normal:
        humidity_deviation = current_humidity - humidity_max_normal
        humidity_normal = False
        humidity_recommendation = "Проверьте вентиляцию и источники избыточной влаги."
        print(f"   Влажность ВЫШЕ нормы на {humidity_deviation:.2f} процентного пункта.")
    else:
        humidity_normal = True
        humidity_recommendation = "Коррекция влажности не требуется."
        print("   Влажность в норме.")

    print()
    print(f"   Протечка: {'ОБНАРУЖЕНА' if leak_detected else 'не обнаружена'}")
    # Протечка имеет приоритет над отклонениями микроклимата.
    if leak_detected:
        status = "АВАРИЯ"
        recommendation = "Обнаружена протечка: немедленно сообщите службе эксплуатации."
    elif not temperature_normal or not humidity_normal:
        status = "ПРЕДУПРЕЖДЕНИЕ"
        recommendation = "Есть отклонения микроклимата. Проверьте указанные параметры."
    else:
        status = "НОРМА"
        recommendation = "Показатели помещения в норме."
else:
    # Не генерируем и не анализируем показания недоступного устройства.
    status = "НЕТ ДАННЫХ"
    recommendation = "Восстановите работу датчика и повторите проверку помещения."
    print("   Измерения не получены: датчик отключён или батарея разряжена.")

print()
print("=" * 60)
print("ИТОГОВЫЙ ОТЧЁТ")
print("=" * 60)
print(f"ID отчёта: {report_id}")
print(f"Статус помещения: {status}")
print(f"Рекомендация: {recommendation}")
if sensor_available:
    print(f"Температура: {temperature_recommendation}")
    print(f"Влажность: {humidity_recommendation}")
if not sensor_active:
    print("Обслуживание: проверьте подключение датчика.")
if sensor_battery_level < 20:
    print("Обслуживание: замените или зарядите батарею датчика.")
print("=" * 60)
