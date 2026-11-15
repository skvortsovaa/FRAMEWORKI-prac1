# ПР10 Администрирование SmartSpace Monitor и Django ORM

Практика продолжает ПР9. Примечание к таблице оценивания на стр. 175 разрешает
демонстрацию собственного проекта. Поэтому Roomly сопоставлен с мониторингом:
Room — помещение, Sensor — оборудование, Metric — показатель, Report — проверка,
Reading — измерение. Пользователи и группы — стандартные модели Django auth.
Бронирования, вместимость и отмены к нашей предметной области не относятся.

## Запуск и вход

Из корня репозитория в PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py import_pr7
.\.venv\Scripts\python.exe manage.py setup_pr10_roles
.\.venv\Scripts\python.exe manage.py createsuperuser
$env:SMARTSPACE_DEBUG = "1"
.\.venv\Scripts\python.exe manage.py runserver 8010
```

Если локальный администратор уже создан, повторять createsuperuser не нужно.
Доступ к подготовленной локальной базе: `.demo/pr10-admin.txt`, файл исключён
из Git. После клонирования создаётся свой администратор. Данные проекта и
учётные записи не включаются в репозиторий. Панель: `/admin/`.

## Соответствие 30 показателям

| № | Показать | Где и что объяснить |
| --- | --- | --- |
| 1 | Админка моделей | Room, Sensor, Metric, Report, Reading и стандартный User. Столбцы, поиск, фильтры, ordering, list_per_page в трёх admin.py. |
| 2 | Связи и inline | Карточка Room: редактируемый SensorInline и исторический ReportInline; карточка Report: ReadingInline. PROTECT запрещает удаление используемых объектов. |
| 3 | Модель и миграции | rooms_web/migrations/0002_pr10_admin_fields.py добавляет slug, is_large и подсказку к площади; migrate применяет изменения, makemigrations создаёт описание. |
| 4 | Преобразование существующих данных | RunPython заполняет slug существующих помещений: сначала nullable unique, затем заполнение и NOT NULL. TextChoices уже реализованы в ПР9; старого is_cancelled у мониторинга нет, фиктивной миграции статусов нет. |
| 5 | Django shell | Импорт моделей, изменение поля в памяти, save(), refresh_from_db(). Пример ниже внутри откатываемой транзакции. |
| 6 | CRUD | Создать временный Room, изменить площадь, удалить. Тест test_pr10_admin_crud_room_and_inline_sensor проверяет полный сценарий через HTTP админки. |
| 7 | Несколько условий | Report.objects.for_date(day).for_room(room).warnings(); QuerySet остаётся цепочкой. |
| 8 | Связанные поля | Report.objects.filter(room__floor=3), Sensor.objects.filter(room__name__contains="Серверная"). Двойное подчёркивание задаёт переход по связи. |
| 9 | Свой менеджер | ReportQuerySet: normal(), warnings(), alarms(), no_data(), with_data(), for_date(), for_room(); Report.objects не скрывает записи. Методы используются в orm_views.py. |
| 10 | Ввод пользователя | smartspace_web/query_params.py: даты, диапазоны, числа; некорректный фильтр даёт пояснение и пустую выборку. |
| 11 | Динамическая сортировка | REPORT_ORDERS, разрешённые ключи newest/oldest/room/status, дополнительный id обеспечивает стабильный порядок. |
| 12 | values() | reports_web/orm_views.py, readings(): выбираются только поля измерения, названия помещения и показателя, единица. Возвращаются словари. |
| 13 | annotate() и F() | readings() и statistics(): имена связанных моделей, Count/Min/Max/Avg. Агрегаты не требуют обхода объектов в Python. |
| 14 | Объект или 404 | room_detail_slug(): get_object_or_404(Room.objects.select_related("sensor"), slug=slug). Несуществующий slug возвращает 404. |
| 15 | Slug и URL | Room.slug, get_absolute_url(), reverse("rooms:detail-slug"), маршрут <slug:slug>. Ссылка «Смотреть на сайте» ведёт к публичной карточке. |
| 16 | GeneratedField | Room.is_large: площадь >= 50 м², db_persist=True. Вводить признак вручную нельзя; после update()/save() нужен refresh_from_db(). |
| 17 | Статистика | /reports/statistics/: статусы, аварии, проверки без данных, помещения с нулём проверок, статистика показателей. |
| 18 | Q | Поиск отчётов объединяет историческое имя, текущее имя помещения и ID через OR. В статистике Q задаёт условные Count. |
| 19 | select_related | Список и карточка Report загружают room через JOIN, Sensor — room; админка использует list_select_related. |
| 20 | Анализ SQL | Debug Toolbar → SQL; manage.py audit_pr10 воспроизводит измерения и показывает query/explain. Сравнение JOIN и prefetch приведено ниже. |
| 21 | Фильтры и пагинация | /reports/: дата, статус, помещение, поиск, сортировка, размер страницы. includes/pagination.html сохраняет GET-параметры через querystring. Тест использует 13 временных отчётов. |
| 22 | Состояние помещения на дату | /rooms/uninspected/?date=2026-09-21: ~Exists(Report.objects.for_date(day).filter(room_id=OuterRef("pk"))). Любая сохранённая проверка, включая НЕТ ДАННЫХ, является фактом проверки. Это не выбор свободных залов. |
| 23 | Контекстный процессор | room_context зарегистрирован в TEMPLATES, передаёт site_name и navigation_rooms_count. Счётчик используется на всех обычных страницах, запрашивается один раз при рендеринге. |
| 24 | TextChoices | Status.NORMAL/WARNING/ALARM/NO_DATA используются в моделях, фильтрах, статистике и менеджере. Статус исторического отчёта согласован со снимком показаний. |
| 25 | Связанные данные без N+1 | readings().values(..., room_name=F("sensor__room__name"), metric_name=F("metric__name")) формирует один JOIN-запрос. Для словарей дополнительный select_related не нужен. |
| 26 | Пересчёт и снимки | Изменить площадь временного помещения через F и получить is_large. Отключение датчика меняет его текущую доступность, но не sensor_active и статус прошлого отчёта. |
| 27 | Именованные маршруты | Карточки Room и ссылки из отчётов/датчиков используют get_absolute_url(). Старые /rooms/<int:room_id>/ сохранены для ПР6/ПР7. |
| 28 | Ошибка базы | database_page перехватывает DatabaseError и возвращает 503. Счётчик навигации выдерживает ошибку БД, не вызывая рекурсии страницы ошибки. Проверяется mock, рабочая БД не повреждается. |
| 29 | Согласованность миграций | manage.py check; manage.py makemigrations --check --dry-run; manage.py showmigrations. Отдельный тест проверяет обновление базы ПР9 с одинаковыми кириллическими именами. |
| 30 | Тест пользовательского сценария | tests/test_orm.py: test_pr10_slug_unique_stable_and_public_links, test_combined_filters_pagination_and_querystrings, права админки, CRUD, статусы и миграция. |

## Административные действия и права

Room: площадь редактируется прямо в списке; датчик — внутри карточки.
Sensor: active и battery доступны в списке, выбор помещения поддерживает autocomplete.
Массовые действия включают и отключают выбранные датчики через update().
В них меняется только булево поле, для которого дополнительных преобразований нет.
ID и помещение датчика с историческими измерениями доступны только для чтения.

Report и Reading доступны только для просмотра, в том числе суперпользователю.
Изменение статуса отдельно от показаний разрушило бы исторический снимок.
Вместо искусственных отмен демонстрируются массовые действия над текущими датчиками.
Наблюдатели получают пять view-разрешений командой setup_pr10_roles, которая
повторяется безопасно. Для входа назначенному сотруднику отдельно нужен is_staff.
Разрешения пользователя суммируются с разрешениями всех его групп.

## Примеры для Django shell

```python
from datetime import date
from django.db import transaction
from django.db.models import F, Q, Count, Prefetch
from rooms_web.models import Room
from reports_web.models import Report, Reading, Status

Report.objects.for_date(date(2026, 9, 21)).warnings()
Report.objects.filter(Q(status=Status.ALARM) | Q(status=Status.WARNING))
Room.objects.values("name").annotate(checks=Count("reports"))
Reading.objects.values("id", metric_name=F("metric__name"))
print(Report.objects.select_related("room").query)
print(Report.objects.select_related("room").explain())
Room.objects.prefetch_related(Prefetch("reports", queryset=Report.objects.alarms()))

with transaction.atomic():
    room = Room.objects.create(name="ПР10 демонстрация", area=49)
    print(room.get_absolute_url())
    Room.objects.filter(pk=room.pk).update(area=F("area") + 1)
    room.refresh_from_db()
    print(room.area, room.is_large)  # 50.0, True
    room.delete()
    transaction.set_rollback(True)
```

Статусы обычных отчётов не назначаются произвольно: full_clean() сверяет их
с сохранённой температурой, влажностью и протечкой. save() сам full_clean()
не вызывает. При массовом update() валидация и save() не запускаются.

## Фактические результаты SQL

На рабочих данных ПР9: 2 помещения, 2 датчика, 3 показателя, 1 отчёт, 3 измерения.
Запросы измерены для полного рендеринга ответа при DEBUG=False,
без сессии администратора и без SQL самой панели отладки.

| Страница | Запросов | Назначение |
| --- | ---: | --- |
| Главная | 1 | Общий COUNT навигации |
| Помещения | 2 | Список и общий COUNT |
| Датчики | 2 | JOIN помещения и общий COUNT |
| История проверок | 4 | COUNT пагинации, список с JOIN, варианты помещений, общий COUNT |
| История с фильтром или страницей | 4 | Те же операции; при пустом наборе отдельные запросы могут пропускаться |
| Карточка отчёта | 2 | JOIN и общий COUNT |
| Карточка помещения по slug | 2 | LEFT JOIN датчика и общий COUNT |
| Измерения | 3 | values с JOIN, показатели, общий COUNT |
| Статистика | 7 | Шесть содержательных агрегатов/выборок и общий COUNT |

Для одного отчёта обращение к room без JOIN выполняет 2 запроса,
с select_related — 1. Для двух помещений с обратными reports обычный обход
выполняет 3 запроса, prefetch_related — 2. Эти числа относятся к указанному набору.
Тест списка увеличивает число строк и подтверждает, что число запросов остаётся 4.
Уже оптимизированные в ПР9 запросы сохранены. Дополнительный COUNT по сравнению
с ПР9 появился из-за требуемого общего контекста навигации.

Debug Toolbar проверен в браузере на отфильтрованной истории: 4 запроса,
включая INNER JOIN Room, московскую дату, статус, ORDER BY и LIMIT.
Скриншоты сохранены в `docs/pr10/screenshots/`. На рабочей базе только один отчёт;
сценарий нескольких страниц проверяется на временных данных в тестах.

## Контрольные команды

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py audit_pr10
.\.venv\Scripts\python.exe manage.py demo_orm
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m flake8 .
git diff --check
git log -2 --oneline
```

Ветка ПР10: `pr10-django-admin`. Первый коммит: `8c0c402` — админка,
модели, миграции, QuerySet и тесты. Второй — документация и подтверждения SQL.
Учебная часть Яндекс Практикума выполнена пользователем; код Блогикум
и учебный аккаунт в этой работе не изменялись.

Основания решений: официальная документация Django 5.2:
[ModelAdmin](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/),
[GeneratedField](https://docs.djangoproject.com/en/5.2/ref/models/fields/#generatedfield),
[менеджеры и QuerySet](https://docs.djangoproject.com/en/5.2/topics/db/managers/).
