from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "evaluacion"

urlpatterns = [
    path("", views.CorridaListaView.as_view(), name="lista"),
    path("<int:pk>/", views.CorridaDetalleView.as_view(), name="detalle"),
    path("<int:pk>/notas/", views.guardar_notas, name="guardar_notas"),
    path("exportar/", views.exportar_csv, name="exportar_csv"),
]

# Rutas DRF (montadas bajo /api/ por webapp/config/urls.py, no bajo /evaluacion/).
_router_api = DefaultRouter()
_router_api.register("evaluacion", views.CorridaEvaluacionViewSet, basename="api-evaluacion")

api_urlpatterns = _router_api.urls
