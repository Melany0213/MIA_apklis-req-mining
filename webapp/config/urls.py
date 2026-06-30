"""URLs raíz del proyecto."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("evaluacion/", include("webapp.apps.requisitos.urls")),
    path("api/opiniones/", include("webapp.apps.opiniones.urls")),
    path("api/validacion/", include("webapp.apps.validacion.urls")),
]
