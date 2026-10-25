from django.urls import path

from . import sql_views, views


app_name = "reports"

urlpatterns = [
    path("statistics/", sql_views.statistics, name="statistics"),
    path("readings/", sql_views.readings, name="readings"),
    path("", views.report_list, name="list"),
    path("<str:report_id>/", views.report_detail, name="detail"),
]
