from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "validacion"

urlpatterns = [
    path("", views.ColaValidacionView.as_view(), name="cola"),
    path("<int:pk>/", views.validar, name="validar"),
    path("<int:pk>/descartar/", views.descartar, name="descartar"),
]

# Rutas DRF (montadas bajo /api/ por webapp/config/urls.py, no bajo /validacion/).
_router_api = DefaultRouter()
_router_api.register("requisitos", views.RequisitoViewSet, basename="api-requisito")

api_urlpatterns = _router_api.urls
