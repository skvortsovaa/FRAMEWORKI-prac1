from django.urls import path

from . import views


urlpatterns = [
    path("", views.report_list, name="report_list"),
    path("<str:report_id>/", views.report_detail, name="report_detail"),
]
