from html import escape

from django.http import HttpResponse
from django.urls import reverse

from homepage.views import data_unavailable, page
from smartspace_web.data import load_project_data


def status_badge(status):
    """Оформить сохранённый статус, не пересчитывая историю."""
    colors = {
        "НОРМА": "text-bg-success",
        "ПРЕДУПРЕЖДЕНИЕ": "text-bg-warning",
        "АВАРИЯ": "text-bg-danger",
        "НЕТ ДАННЫХ": "text-bg-secondary",
    }
    return f'<span class="badge {colors[status]}">{escape(status)}</span>'


def metric_row(label, analysis, unit):
    """Показание и границы берутся из исторического MetricAnalysis."""
    if analysis is None:
        value, limits, state = "Нет данных", "—", "Нет данных"
    else:
        value = f"{analysis.value:g} {unit}"
        limits = f"{analysis.minimum:g}–{analysis.maximum:g} {unit}"
        state = "В норме" if analysis.normal else "Вне нормы"
    return f"""
    <tr>
        <th scope="row">{label}</th>
        <td>{value}</td><td>{limits}</td><td>{state}</td>
    </tr>
    """


def report_list(request):
    """История объектов Report в порядке сохранения в JSON."""
    try:
        data = load_project_data()
    except (OSError, ValueError):
        return data_unavailable()

    rows = []
    for report in data.reports:
        detail_url = escape(reverse("report_detail", args=[report.id]))
        checked_at = escape(report.checked_at.replace("T", " ", 1))
        rows.append(f"""
        <tr>
            <th scope="row"><a href="{detail_url}">{checked_at}</a></th>
            <td>{escape(report.room_name)}</td>
            <td>{status_badge(report.status)}</td>
        </tr>
        """)
    if rows:
        content = f"""
        <h1>История проверок</h1>
        <p class="text-secondary">Всего проверок: {len(data.reports)}</p>
        <div class="card shadow-sm">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0"
                       aria-label="История проверок">
                    <thead class="table-light">
                        <tr>
                            <th scope="col">Дата и время проверки</th>
                            <th scope="col">Помещение при проверке</th>
                            <th scope="col">Статус</th>
                        </tr>
                    </thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </div>
        </div>
        """
    else:
        content = """
        <h1>История проверок</h1>
        <p class="text-secondary">Проверок пока нет.</p>
        """
    return HttpResponse(page("История проверок", content))


def report_detail(request, report_id):
    """Показать сохранённый снимок проверки и связь с помещением."""
    try:
        data = load_project_data()
    except (OSError, ValueError):
        return data_unavailable()

    list_url = reverse("report_list")
    report = next(
        (item for item in data.reports if item.id == report_id), None,
    )
    if report is None:
        content = f"""
        <h1 class="text-danger">Отчёт не найден</h1>
        <p>В истории нет отчёта с указанным идентификатором.</p>
        <a href="{list_url}" class="btn btn-outline-primary">
            К истории проверок
        </a>
        """
        return HttpResponse(page("Отчёт не найден", content), status=404)

    room_url = reverse("room_detail", args=[report.room.id])
    checked_at = escape(report.checked_at.replace("T", " ", 1))
    active = "Включён" if report.sensor_active else "Отключён"
    if report.leak_detected is None:
        leak = "Нет данных"
    else:
        leak = "Обнаружена" if report.leak_detected else "Не обнаружена"
    readings = (
        metric_row("Температура", report.temperature, "°C")
        + metric_row("Влажность", report.humidity, "%")
    )
    content = f"""
    <h1>Отчёт проверки</h1>
    <p class="text-secondary text-break">ID: {escape(report.id)}</p>
    <div class="card shadow-sm mb-4">
        <div class="card-body p-4">
            <h2 class="h4">{escape(report.room_name)}</h2>
            <p>{checked_at} · {status_badge(report.status)}</p>
            <p class="text-secondary">
                Название, состояние датчика и нормы сохранены
                на момент проверки.
            </p>
            <p>Датчик при проверке: <strong>{active}</strong>.
                Заряд: <strong>{report.battery}%</strong>.</p>
            <p>Протечка: <strong>{leak}</strong>.</p>
            <a href="{room_url}">Открыть текущее помещение</a>
        </div>
    </div>
    <h2 class="h4">Сохранённые показания</h2>
    <div class="card shadow-sm mb-4">
        <div class="table-responsive">
            <table class="table align-middle mb-0"
                   aria-label="Показания на момент проверки">
                <thead class="table-light">
                    <tr>
                        <th scope="col">Показатель</th>
                        <th scope="col">Значение</th>
                        <th scope="col">Норма при проверке</th>
                        <th scope="col">Результат</th>
                    </tr>
                </thead>
                <tbody>{readings}</tbody>
            </table>
        </div>
    </div>
    <a href="{list_url}" class="btn btn-outline-primary">
        К истории проверок
    </a>
    """
    return HttpResponse(page(f"Отчёт {report.id}", content))
