"""Pruebas de `GET /api/opiniones/` (corpus de solo lectura vía DRF)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from webapp.apps.opiniones.models import Opinion


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_lista_opiniones_devuelve_json_sin_login(api_client):
    Opinion.objects.create(texto_original="la app se cierra sola", aplicacion="Apklis")
    Opinion.objects.create(texto_original="muy buena app", aplicacion="Todus")

    respuesta = api_client.get("/api/opiniones/")

    assert respuesta.status_code == 200
    textos = {fila["texto_original"] for fila in respuesta.data}
    assert textos == {"la app se cierra sola", "muy buena app"}


@pytest.mark.django_db
def test_lista_opiniones_filtra_por_aplicacion(api_client):
    Opinion.objects.create(texto_original="opinión de Apklis", aplicacion="Apklis")
    Opinion.objects.create(texto_original="opinión de Todus", aplicacion="Todus")

    respuesta = api_client.get("/api/opiniones/", {"aplicacion": "Apklis"})

    assert respuesta.status_code == 200
    assert len(respuesta.data) == 1
    assert respuesta.data[0]["texto_original"] == "opinión de Apklis"
