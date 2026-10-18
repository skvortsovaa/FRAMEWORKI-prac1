from html import escape

from django.http import HttpResponse
from django.urls import reverse

from homepage.views import data_unavailable, page
from smartspace_web.data import load_project_data


def sensor_list(request):
    """Показать датчики ПР3 и связанные с ними помещения."""
    try:
        data = load_project_data()
    except (OSError, ValueError):
        return data_unavailable()

    rows = []
    for sensor in data.sensors:
        room_url = reverse("room_detail", args=[sensor.room.id])
        available = sensor.is_available()
        status = "Доступен" if available else "Недоступен"
        badge = "text-bg-success" if available else "text-bg-secondary"
        active = "Включён" if sensor.active else "Отключён"
        battery_note = (
            '<div class="small text-warning-emphasis">'
            'Низкий заряд: рекомендуется обслуживание.</div>'
            if sensor.battery < 20 else ""
        )
        rows.append(f"""
        <tr>
            <th scope="row">{escape(sensor.id)}</th>
            <td><a href="{room_url}">{escape(sensor.room.name)}</a></td>
            <td>{active}</td>
            <td>{sensor.battery}%{battery_note}</td>
            <td><span class="badge {badge}">{status}</span></td>
        </tr>
        """)

    if rows:
        content = f"""
        <h1>Датчики</h1>
        <p class="text-secondary">Всего датчиков: {len(data.sensors)}</p>
        <div class="card shadow-sm">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0"
                       aria-label="Список датчиков">
                    <thead class="table-light">
                        <tr>
                            <th scope="col">ID датчика</th>
                            <th scope="col">Помещение</th>
                            <th scope="col">Активность</th>
                            <th scope="col">Заряд</th>
                            <th scope="col">Доступность</th>
                        </tr>
                    </thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </div>
        </div>
        <p class="text-secondary mt-3">
            Датчик доступен, если он включён и заряд больше нуля.
        </p>
        """
    else:
        content = """
        <h1>Датчики</h1>
        <p class="text-secondary">Датчики пока не добавлены.</p>
        """
    return HttpResponse(page("Датчики", content))
