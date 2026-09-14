# SmartSpace Monitor - Начальная версия
# Программа симулирует работу датчика температуры в помещении

import datetime  # Импорт модуля для работы с датой и временем
import random    # Импорт модуля для генерации случайных чисел

# ОСНОВНЫЕ СУЩНОСТИ (простые типы данных)

# Сущность "Помещение"
room_name = "Серверная №1"        # строка (str)
room_floor = 3                     # целое число (int)
room_area = 25.5                   # вещественное число (float)

# Сущность "Датчик"
sensor_id = "SENS-001"             # строка (str)
sensor_active = True               # булево значение (bool)
sensor_battery_level = 85          # целое число (int) - процент заряда

# Сущность "Показатель"
metric_name = "Температура"        # строка (str)
metric_unit = "°C"                 # строка (str)
metric_min_normal = 18.0           # вещественное число (float)
metric_max_normal = 24.0           # вещественное число (float)

# СИМУЛЯЦИЯ ПОЛУЧЕНИЯ ДАННЫХ ОТ ДАТЧИКА

print("=" * 60)
print("SMARTSPACE MONITOR - Система мониторинга помещений")
print("=" * 60)
print()

# Генерация случайного показания температуры (симуляция датчика)
# random.uniform() генерирует случайное вещественное число в диапазоне
current_temperature = random.uniform(16.0, 28.0)

# Получение текущего времени
current_time = datetime.datetime.now()

# ОБРАБОТКА ДАННЫХ С ИСПОЛЬЗОВАНИЕМ ВЕТВЛЕНИЙ

print(f"Время измерения: {current_time.strftime('%d.%m.%Y %H:%M:%S')}")
print()
print("ИНФОРМАЦИЯ О ПОМЕЩЕНИИ:")
print(f"   Название: {room_name}")
print(f"   Этаж: {room_floor}")
print(f"   Площадь: {room_area} кв.м")
print()
print(" ИНФОРМАЦИЯ О ДАТЧИКЕ:")
print(f"   ID датчика: {sensor_id}")
print(f"   Статус: {'Активен' if sensor_active else 'Неактивен'}")
print(f"   Заряд батареи: {sensor_battery_level}%")
print()
print(" ПОКАЗАНИЯ:")
print(f"   Показатель: {metric_name}")
print(f"   Текущее значение: {current_temperature:.2f} {metric_unit}")
print(f"   Норма: от {metric_min_normal} до {metric_max_normal} {metric_unit}")
print()

# Проверка статуса датчика (ветвление if-else)
if not sensor_active:
    print(" ВНИМАНИЕ: Датчик неактивен! Данные могут быть неточными.")
elif sensor_battery_level < 20:
    print("ВНИМАНИЕ: Низкий заряд батареи датчика!")
else:
    print("Датчик работает нормально")

print()

# Анализ показания (ветвление if-elif-else)
print("АНАЛИЗ ПОКАЗАНИЙ:")

# Преобразование типов: сравнение float с int
if current_temperature < metric_min_normal:
    # Операции с числами
    deviation = metric_min_normal - current_temperature
    print(f"   Температура НИЖЕ нормы на {deviation:.2f} {metric_unit}")
    status = "critical_cold"
elif current_temperature > metric_max_normal:
    deviation = current_temperature - metric_max_normal
    print(f"   Температура ВЫШЕ нормы на {deviation:.2f} {metric_unit}")
    status = "critical_hot"
else:
    # Вычисление отклонения от середины диапазона
    normal_middle = (metric_min_normal + metric_max_normal) / 2
    deviation_from_middle = abs(current_temperature - normal_middle)
    print(f"   ✅ Температура в норме")
    print(f"   Отклонение от идеала: {deviation_from_middle:.2f} {metric_unit}")
    status = "normal"

print()

# ФОРМИРОВАНИЕ ИТОГОВОГО ОТЧЕТА

report_id = "REP-" + str(current_time.year) + "-" + str(random.randint(1000, 9999))

print("=" * 60)
print("ИТОГОВЫЙ ОТЧЕТ")
print("=" * 60)
print(f"ID отчета: {report_id}")
print(f"Статус помещения: {status.upper()}")

# Определение рекомендации на основе статуса
if status == "critical_cold":
    recommendation = "Рекомендуется включить отопление"
elif status == "critical_hot":
    recommendation = "Рекомендуется включить вентиляцию/кондиционирование"
else:
    recommendation = "Параметры в норме, действий не требуется"

print(f"Рекомендация: {recommendation}")
print("=" * 60)