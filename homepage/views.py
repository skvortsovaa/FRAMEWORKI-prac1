"""Главная страница и общие ответы об ошибках через шаблоны."""

from django.shortcuts import render


def index(request):
    """Описание проекта и переходы к основным разделам."""
    return render(request, "homepage/index.html")


def data_unavailable(request):
    """Не раскрывать подробности ошибки JSON-хранилища посетителю."""
    return render(request, "homepage/data_unavailable.html", status=503)


def page_not_found(request, exception):
    """Общий обработчик неизвестного маршрута при DEBUG=False."""
    return render(request, "404.html", status=404)
