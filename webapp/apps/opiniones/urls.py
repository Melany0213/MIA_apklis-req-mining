from django.urls import path

from . import views

app_name = "opiniones"

urlpatterns = [
    path("", views.OpinionListaView.as_view(), name="lista"),
    path("subir/", views.subir, name="subir"),
]
