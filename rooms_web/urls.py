from django.urls import path

from . import views


app_name = "rooms"

urlpatterns = [
    path("uninspected/", views.uninspected_rooms, name="uninspected"),
    path("", views.room_list, name="list"),
    path("<int:room_id>/", views.room_detail, name="detail"),
]
