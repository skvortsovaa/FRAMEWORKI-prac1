from html import escape

from django.http import HttpResponse
from django.urls import reverse

from homepage.views import data_unavailable, page
from models.rooms import get_room
from models.sensors import get_room_sensor
from smartspace_web.data import load_project_data


def room_list(request):
    """Список объектов Room, загруженных средствами ПР3."""
    try:
        data = load_project_data()
    except (OSError, ValueError):
        return data_unavailable()

    query = request.GET.get("room_id", "").strip()
    rooms = data.rooms
    message = ""
    message_style = "info"
    if query:
        rooms = []
        try:
            if not query.isascii() or not query.isdecimal():
                raise ValueError
            room_id = int(query)
            if room_id <= 0:
                raise ValueError
        except ValueError:
            message = (
                "Введите ID помещения — положительное целое число, "
                "например 1."
            )
            message_style = "warning"
        else:
            try:
                rooms = [get_room(data.rooms, room_id)]
            except ValueError:
                message = f"Помещение с ID {escape(query)} не найдено."
            else:
                message = (
                    "Помещение найдено. Нажмите на название, "
                    "чтобы открыть карточку."
                )
                message_style = "success"

    list_url = reverse("room_list")
    content = f"""
    <h1>Помещения</h1>
    <form method="get" action="{list_url}" class="card shadow-sm mb-4"
          role="search" aria-label="Поиск помещения по ID">
        <div class="card-body p-4">
            <div class="row g-3 align-items-end">
                <div class="col-12 col-md-6">
                    <label for="room-id" class="form-label">
                        ID помещения
                    </label>
                    <input type="text" inputmode="numeric" class="form-control"
                           id="room-id" name="room_id" value="{escape(query)}"
                           placeholder="Например, 1"
                           aria-describedby="room-id-help">
                </div>
                <div class="col-12 col-md-auto d-flex gap-2 flex-wrap">
                    <button type="submit" class="btn btn-primary">
                        Найти
                    </button>
                    <a href="{list_url}" class="btn btn-outline-secondary">
                        Сбросить поиск
                    </a>
                </div>
            </div>
            <div id="room-id-help" class="form-text mt-2">
                Введите положительное целое число.
                Пустое поле покажет все помещения.
            </div>
        </div>
    </form>
    """
    if message:
        content += (
            f'<div class="alert alert-{message_style}" role="status">'
            f'{message}</div>'
        )

    rows = []
    for room in rooms:
        detail_url = reverse("room_detail", args=[room.id])
        rows.append(f"""
        <tr>
            <td>{room.id}</td>
            <th scope="row"><a href="{detail_url}">
                {escape(room.name)}
            </a></th>
            <td>{room.floor}</td>
            <td>{room.area:g} м²</td>
        </tr>
        """)

    if rows:
        count_label = "Найдено помещений" if query else "Всего помещений"
        content += f"""
        <p class="text-secondary">{count_label}: {len(rooms)}</p>
        <div class="card shadow-sm">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0"
                       aria-label="Список помещений">
                    <thead class="table-light">
                        <tr>
                            <th scope="col">ID</th>
                            <th scope="col">Помещение</th>
                            <th scope="col">Этаж</th>
                            <th scope="col">Площадь</th>
                        </tr>
                    </thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </div>
        </div>
        """
    elif not query:
        content += """
        <p class="text-secondary">Помещения пока не добавлены.</p>
        """
    return HttpResponse(page("Помещения", content))


def room_detail(request, room_id):
    """Найти Room и показать его атрибуты и связанный объект Sensor."""
    try:
        data = load_project_data()
    except (OSError, ValueError):
        return data_unavailable()

    list_url = reverse("room_list")
    try:
        room = get_room(data.rooms, room_id)
    except ValueError:
        content = f"""
        <h1 class="text-danger">Помещение не найдено</h1>
        <p>Помещения с ID {room_id} нет в списке.</p>
        <a href="{list_url}" class="btn btn-outline-primary">
            К списку помещений
        </a>
        """
        return HttpResponse(page("Помещение не найдено", content), status=404)

    sensor = get_room_sensor(data.sensors, room.id)
    available = sensor.is_available()
    status = "Доступен" if available else "Недоступен"
    badge = "text-bg-success" if available else "text-bg-secondary"
    active = "Включён" if sensor.active else "Отключён"
    battery_note = (
        '<p class="text-warning-emphasis">'
        'Низкий заряд: рекомендуется обслуживание датчика.</p>'
        if sensor.battery < 20 else ""
    )
    content = f"""
    <h1>{escape(room.name)}</h1>
    <p class="text-secondary">Помещение №{room.id}</p>
    <div class="row g-4 mb-4">
        <section class="col-12 col-md-6">
            <div class="card h-100 shadow-sm">
                <div class="card-body p-4">
                    <h2 class="h4">О помещении</h2>
                    <dl class="mb-0">
                        <dt>ID</dt><dd>{room.id}</dd>
                        <dt>Этаж</dt><dd>{room.floor}</dd>
                        <dt>Площадь</dt><dd>{room.area:g} м²</dd>
                    </dl>
                </div>
            </div>
        </section>
        <section class="col-12 col-md-6">
            <div class="card h-100 shadow-sm">
                <div class="card-body p-4">
                    <h2 class="h4">Датчик помещения</h2>
                    <p><span class="badge {badge}">{status}</span></p>
                    <dl>
                        <dt>ID датчика</dt><dd>{escape(sensor.id)}</dd>
                        <dt>Активность</dt><dd>{active}</dd>
                        <dt>Заряд</dt><dd>{sensor.battery}%</dd>
                    </dl>
                    {battery_note}
                </div>
            </div>
        </section>
    </div>
    <a href="{list_url}" class="btn btn-outline-primary">
        К списку помещений
    </a>
    """
    return HttpResponse(page(room.name, content))
