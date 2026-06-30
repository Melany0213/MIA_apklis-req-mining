from django.urls import path

from . import views

app_name = "evaluacion"

urlpatterns = [
    path("", views.CorridaListaView.as_view(), name="lista"),
    path("<int:pk>/", views.CorridaDetalleView.as_view(), name="detalle"),
    path("<int:pk>/notas/", views.guardar_notas, name="guardar_notas"),
    path("exportar/", views.exportar_csv, name="exportar_csv"),
]
