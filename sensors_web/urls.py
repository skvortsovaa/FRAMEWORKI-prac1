from django.urls import path

from . import views


app_name = "sensors"

urlpatterns = [
    path("", views.sensor_list, name="list"),
]
