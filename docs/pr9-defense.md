# ПР9 — карта демонстрации SmartSpace Monitor

Тема: модели Django, связи и операции с базой данных через ORM.
Roomly из методички адаптирован к мониторингу помещений: вместо бронирований
используются отчёты проверок. Отчёт «НЕТ ДАННЫХ» означает проведённую попытку
проверки, поэтому учитывается при поиске непроверенных помещений; отменённых
бронирований в этой предметной области нет.

## Перед защитой

Все команды выполняются из корня `FRAMEWORKI-prac1`:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py demo_orm
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m flake8 .
```

Для просмотра SQL в браузере:

```powershell
$env:SMARTSPACE_DEBUG = "1"
.\.venv\Scripts\python.exe manage.py runserver 8009
# После завершения сервера:
Remove-Item Env:SMARTSPACE_DEBUG
```

Открыть `/reports/` и панель SQL в Django Debug Toolbar. Запрос списка
соединяет отчёты с помещениями. На `/reports/readings/` используется `values()`:
нужные поля выбираются через JOIN без создания объектов связанных моделей.
Настройка панели соответствует официальной
[инструкции Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/en/latest/installation.html).

## 30 пунктов таблицы 7.3

| № | Что показать в нашем проекте |
| --- | --- |
| 1 | `rooms_web/models.py`: `Room`, `CharField`, `IntegerField`, `FloatField`; изменение поля требует новой миграции. |
| 2 | `reports_web/models.py`: `Report.room`, `Reading.sensor/metric/report`, `on_delete=PROTECT`, обратные `reports/readings`. |
| 3 | В shell: `report.room.name`, `room.reports.all()`, `room.sensor`; прямая и обратная связь, роль `related_name`. |
| 4 | `makemigrations`, `showmigrations`, `migrate`; три начальные миграции применены. |
| 5 | `manage.py demo_orm`: `Room.objects.create(name=..., floor=1, area=20)`; показать появившийся ID. |
| 6 | Изменение площади через `save(update_fields=["area"])`, чтение после `refresh_from_db()`; в demo_orm итоговый откат. |
| 7 | Удаление помещения с датчиком вызывает `ProtectedError`; после удаления учебного датчика удаляется помещение. |
| 8 | `/rooms/`: `Room.objects.all()`; добавить `filter(area__gte=30)` в shell и сравнить результат. |
| 9 | `/sensors/?q=серверная`: поиск по `room__name`; фильтр `room__pk` отличается от поиска имени связанной модели. |
| 10 | `/reports/?date=2026-09-21&status=ПРЕДУПРЕЖДЕНИЕ&room_id=1`: совместная фильтрация. |
| 11 | `smartspace_web/query_params.py`: преобразование числа/даты; `/reports/?date=bad` показывает сообщение без ошибки сервера. |
| 12 | `/reports/?sort=oldest` против `sort=newest`: `checked_at` против `-checked_at`, затем стабильный ID. |
| 13 | Словарь `REPORT_ORDERS`; `/reports/?sort=room`: связанное имя, время, ID; неизвестное значение отклоняется. |
| 14 | `readings()` в `reports_web/orm_views.py`: `values()` возвращает словари с конкретными полями, включая связанные. |
| 15 | Там же: именованные выражения `room_name=F("sensor__room__name")`, `metric_name=F("metric__name")`; аргументы values используют аннотирование. |
| 16 | `/rooms/99999/` и `/reports/missing/`: шаблон с понятным сообщением и HTTP 404. |
| 17 | `/reports/statistics/`: `aggregate`, условный `Count`, `Sum` площади. |
| 18 | Там же: `values().annotate()`, группировка по помещениям/статусам/показателям; `Min/Max/Avg`. |
| 19 | `Report.objects.select_related("room")`, `Sensor.objects.select_related("room")`; нет N+1, проверено тестом. |
| 20 | `readings()` в `reports_web/orm_views.py`: `values` + `F` выбирают только нужные столбцы; `select_related` здесь не требуется. |
| 21 | В `report_list` ключ `reports` передаётся в шаблон, цикл отображает объекты ORM из текущей страницы. |
| 22 | `Paginator(reports, size)`, GET `page_size` от 1 до 100. |
| 23 | `templates/includes/pagination.html`: `has_previous`, `has_next`, первая/последняя страницы. |
| 24 | `{% querystring page=... %}` сохраняет фильтры и сортировку при переходах. |
| 25 | Порядок: проверка ввода → filter/exclude → order_by → Paginator → render. |
| 26 | Статистика включает помещения без проверок и показатели без измерений; `Count` равен 0. |
| 27 | `/reports/?exclude_no_data=1`: `exclude(status=Status.NO_DATA)`. |
| 28 | `/reports/readings/?limit=2&offset=1`: срез QuerySet `[start:start + page_size]`. |
| 29 | `get()` возвращает объект, при отсутствии — `DoesNotExist`, при неуникальном условии — `MultipleObjectsReturned`; `filter()` возвращает QuerySet. |
| 30 | Показать одну цепочку целиком: URL → `views.py` → `orm_views.py` → модели → контекст → шаблон. |

## Django shell и выгрузка

```python
from rooms_web.models import Room
from reports_web.models import Report, Reading

room = Room.objects.get(pk=1)
print(room.sensor.is_available())
print(list(room.reports.values_list("id", flat=True)))
print(Report.objects.select_related("room").query)
print(Reading.objects.select_related("sensor__room", "metric").query)
```

```powershell
.\.venv\Scripts\python.exe manage.py dumpdata rooms_web sensors_web reports_web --indent 2 --output .demo/pr9-fixture.json
# Загружать в совместимую учебную базу после migrate:
.\.venv\Scripts\python.exe manage.py loaddata .demo/pr9-fixture.json
```

`dumpdata` сохраняет данные, а миграции — структуру. `loaddata` может менять
совпадающие ID: для демонстрации используется копия базы. В исходной истории
один отчёт; пагинация на 13 дополнительных отчётах проверяется автоматически
в изолированной тестовой базе (`test_combined_filters_pagination_and_querystrings`).

## Материалы Практикума

Пользователь подтвердил прохождение обоих разделов. Для защиты результат
предъявляется в учебном аккаунте:

- [x] Отношения между таблицами; один к одному; многие к одному; JOIN;
  многие ко многим; изменение таблиц и ссылочная целостность.
- [x] Описание таблиц классами; связи моделей; абстрактные модели;
  миграции; Django shell и CRUD; заполнение БД и выгрузка.

## Что важно объяснить

`ForeignKey` — связь многие к одному; `OneToOneField` у датчика обеспечивает
не более одного датчика на помещение. `room` возвращает объект, `room_id` —
ключ без дополнительного запроса. `related_name` задаёт имя обратной связи.
`PROTECT` сохраняет историю, запрещая удаление используемой записи.

`null=True` допускает NULL в базе, `blank=True` — пустое значение при валидации.
У отсутствующего показания хранится NULL, а отсутствие протечки — False/0.
`full_clean()` проверяет поля и правила модели; `save()` сам его не вызывает.
CHECK/UNIQUE/FK продолжают действовать на уровне базы.

Старая дата без зоны при переносе интерпретируется как Europe/Moscow.
Django хранит время с учётом USE_TZ; шаблоны показывают московское время,
фильтр `checked_at__date` использует ту же зону.

SQL-слой ПР7 оставлен для регрессионных тестов; нормальный веб-режим — ORM.
Прямой sqlite3 в переносе нужен только для чтения отдельной исходной базы.
Ни миграции, ни импорт не пересоздают и не изменяют исходную SQLite.
