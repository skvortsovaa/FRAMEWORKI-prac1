from html import escape

from django.http import HttpResponse
from django.urls import reverse


def page(title, content):
    """Общий HTML-каркас; content содержит разметку представления."""
    bootstrap = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3"
        "/dist/css/bootstrap.min.css"
    )
    home_url = reverse("index")
    rooms_url = reverse("room_list")
    sensors_url = reverse("sensor_list")
    reports_url = reverse("report_list")
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} | SmartSpace Monitor</title>
    <link rel="stylesheet" href="{bootstrap}">
    <style>
        body {{ background: #f4f7fb; color: #172b4d; }}
        .site-header {{ background: #172b4d; }}
        .site-header a {{ color: #fff; }}
        .site-header a:hover {{ color: #b9dcff; }}
        .site-header a:focus-visible {{ outline: 2px solid #b9dcff; }}
        .section-card {{ border-top: 4px solid #0d6efd; }}
    </style>
</head>
<body class="d-flex flex-column min-vh-100">
    <header class="site-header py-3">
        <div class="container">
            <a class="fs-4 fw-semibold text-decoration-none"
               href="{home_url}">SmartSpace Monitor</a>
            <nav class="nav mt-2" aria-label="Основная навигация">
                <a class="nav-link ps-0" href="{home_url}">Главная</a>
                <a class="nav-link" href="{rooms_url}">Помещения</a>
                <a class="nav-link" href="{sensors_url}">Датчики</a>
                <a class="nav-link" href="{reports_url}">История проверок</a>
            </nav>
        </div>
    </header>
    <main class="container py-5 flex-grow-1">{content}</main>
    <footer class="container py-3 border-top text-secondary small">
        SmartSpace Monitor · Учебный проект
    </footer>
</body>
</html>"""


def data_unavailable():
    """Общий ответ при ошибке чтения или проверки данных ПР3."""
    content = f"""
    <h1>Данные временно недоступны</h1>
    <p>Не удалось загрузить данные. Повторите попытку позже.</p>
    <a href="{reverse('index')}" class="btn btn-outline-primary">
        На главную
    </a>
    """
    return HttpResponse(
        page("Данные временно недоступны", content), status=503,
    )


def index(request):
    """Главная страница SmartSpace Monitor."""
    content = f"""
    <h1 class="display-5 fw-semibold">SmartSpace Monitor</h1>
    <p class="lead">Система мониторинга состояния помещений</p>
    <p class="text-secondary mb-4">
        Температура, влажность и протечки: информация о помещениях,
        состоянии датчиков и результатах проверок в одном месте.
    </p>
    <div class="row g-4">
        <section class="col-12 col-md-4">
            <div class="card section-card h-100 shadow-sm">
                <div class="card-body d-flex flex-column p-4">
                    <h2 class="h4 card-title">Помещения</h2>
                    <p class="card-text">
                        Название, этаж и площадь каждого помещения.
                    </p>
                    <a href="{reverse('room_list')}"
                       class="btn btn-primary mt-auto">К помещениям</a>
                </div>
            </div>
        </section>
        <section class="col-12 col-md-4">
            <div class="card section-card h-100 shadow-sm">
                <div class="card-body d-flex flex-column p-4">
                    <h2 class="h4 card-title">Датчики</h2>
                    <p class="card-text">
                        Устройства, их активность и уровень заряда.
                    </p>
                    <a href="{reverse('sensor_list')}"
                       class="btn btn-primary mt-auto">К датчикам</a>
                </div>
            </div>
        </section>
        <section class="col-12 col-md-4">
            <div class="card section-card h-100 shadow-sm">
                <div class="card-body d-flex flex-column p-4">
                    <h2 class="h4 card-title">История проверок</h2>
                    <p class="card-text">
                        Результаты мониторинга и состояние микроклимата.
                    </p>
                    <a href="{reverse('report_list')}"
                       class="btn btn-primary mt-auto">К истории проверок</a>
                </div>
            </div>
        </section>
    </div>
    """
    return HttpResponse(page("Главная", content))


def page_not_found(request, exception):
    """Страница для неизвестного адреса; Django вызывает при DEBUG=False."""
    content = f"""
    <section class="card shadow-sm">
        <div class="card-body p-4 p-md-5">
            <h1 class="text-danger">404 — страница не найдена</h1>
            <p class="lead">Проверьте адрес или вернитесь на главную.</p>
            <a href="{reverse('index')}" class="btn btn-primary">
                На главную
            </a>
        </div>
    </section>
    """
    return HttpResponse(page("404 — страница не найдена", content), status=404)
