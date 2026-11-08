from django.urls import path

from . import views

app_name = "converter"

urlpatterns = [
    path("", views.tool, name="tool"),
    path("start/", views.start, name="start"),
    path("batch/<uuid:batch_id>/status/", views.status, name="status"),
    path("batch/<uuid:batch_id>/delete/", views.delete, name="delete"),
]
