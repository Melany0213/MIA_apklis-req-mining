"""Pruebas de `GET /api/evaluacion/` (métricas de corridas registradas)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from webapp.apps.requisitos.models import CorridaEvaluacion


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_lista_evaluacion_devuelve_json_sin_login(api_client):
    CorridaEvaluacion.objects.create(
        metodo="semantico",
        clasificador="logreg",
        precision_global=0.91,
        recall_global=0.90,
        f1_global=0.905,
        tam_corpus=500,
    )
    CorridaEvaluacion.objects.create(
        metodo="tfidf",
        clasificador="logreg",
        precision_global=0.88,
        recall_global=0.83,
        f1_global=0.847,
        tam_corpus=500,
    )

    respuesta = api_client.get("/api/evaluacion/")

    assert respuesta.status_code == 200
    assert len(respuesta.data) == 2
    metodos = {fila["metodo"] for fila in respuesta.data}
    assert metodos == {"semantico", "tfidf"}
