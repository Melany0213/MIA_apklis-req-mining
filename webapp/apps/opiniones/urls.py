from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "opiniones"

urlpatterns = [
    path("", views.OpinionListaView.as_view(), name="lista"),
    path("subir/", views.subir, name="subir"),
]

# Rutas DRF (montadas bajo /api/ por webapp/config/urls.py, no bajo /corpus/).
_router_api = DefaultRouter()
_router_api.register("opiniones", views.OpinionViewSet, basename="api-opinion")

api_urlpatterns = [
    *_router_api.urls,
    path("clasificar/", views.ClasificarAPIView.as_view(), name="api-clasificar"),
]
