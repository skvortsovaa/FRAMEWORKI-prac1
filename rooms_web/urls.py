from django.urls import path

from . import sql_views, views


app_name = "rooms"

urlpatterns = [
    path("uninspected/", sql_views.uninspected_rooms, name="uninspected"),
    path("", views.room_list, name="list"),
    path("<int:room_id>/", views.room_detail, name="detail"),
]
