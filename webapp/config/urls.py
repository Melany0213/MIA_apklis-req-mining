"""URLs raíz del proyecto."""

from django.contrib import admin
from django.urls import include, path

from webapp.apps.opiniones.urls import api_urlpatterns as _api_opiniones
from webapp.apps.requisitos.urls import api_urlpatterns as _api_evaluacion
from webapp.apps.validacion.urls import api_urlpatterns as _api_validacion

urlpatterns = [
    path("admin/", admin.site.urls),
    path("evaluacion/", include("webapp.apps.requisitos.urls")),
    path("corpus/", include("webapp.apps.opiniones.urls")),
    path("validacion/", include("webapp.apps.validacion.urls")),
    # API REST (DRF) — ver docs/ARQUITECTURA.md §4. Cada app declara su parte
    # del router en su propio urls.py; aquí solo se agrupan bajo /api/.
    path("api/", include([*_api_opiniones, *_api_evaluacion, *_api_validacion])),
]
