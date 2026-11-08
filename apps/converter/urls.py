from django.urls import path

from . import views

app_name = "converter"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("convert/", views.converter, name="converter"),
    path("start/", views.start, name="start"),
    path("batch/<uuid:batch_id>/", views.progress, name="progress"),
    path("batch/<uuid:batch_id>/status/", views.status, name="status"),
    path("batch/<uuid:batch_id>/results/", views.results, name="results"),
    path("batch/<uuid:batch_id>/slot/<int:position>/retry/", views.retry, name="retry"),
    path("batch/<uuid:batch_id>/delete/", views.delete, name="delete"),
]
