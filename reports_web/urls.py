from django.urls import path

from . import views


app_name = "reports"

urlpatterns = [
    path("", views.report_list, name="list"),
    path("<str:report_id>/", views.report_detail, name="detail"),
]
