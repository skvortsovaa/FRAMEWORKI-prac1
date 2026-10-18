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

    rows = []
    for room in data.rooms:
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
        content = f"""
        <h1>Помещения</h1>
        <p class="text-secondary">Всего помещений: {len(data.rooms)}</p>
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
    else:
        content = """
        <h1>Помещения</h1>
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
