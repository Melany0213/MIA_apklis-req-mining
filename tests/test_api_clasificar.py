"""Pruebas de `POST /api/clasificar/`.

Usa un doble de prueba para `nucleo.pipeline.Pipeline` (como
`tests/test_subida_opiniones.py` hace con `obtener_componentes`) para no
cargar spaCy ni el modelo de embeddings reales.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from nucleo.pipeline import Propuesta
from webapp.apps.opiniones.models import Opinion
from webapp.apps.validacion.models import Requisito


class _PipelineFalso:
    def ejecutar(self, opiniones: list[str]) -> list[Propuesta]:
        return [
            Propuesta(
                texto_original=texto,
                texto_preprocesado=texto.lower(),
                etiqueta="RF",
                confianza=0.9,
                metodo="zero_shot",
            )
            for texto in opiniones
        ]


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def pipeline_falso(monkeypatch):
    monkeypatch.setattr("webapp.apps.opiniones.views.obtener_pipeline", lambda: _PipelineFalso())


@pytest.fixture
def usuario_autenticado(django_user_model):
    return django_user_model.objects.create_user(username="analista", password="clave-segura-123")


@pytest.mark.django_db
def test_clasificar_sin_login_no_autorizado(api_client, pipeline_falso):
    respuesta = api_client.post("/api/clasificar/", {"opiniones": ["hola"]}, format="json")

    assert respuesta.status_code in (401, 403)


@pytest.mark.django_db
def test_clasificar_con_login_devuelve_propuestas_sin_persistir(
    api_client, pipeline_falso, usuario_autenticado
):
    api_client.force_authenticate(usuario_autenticado)

    respuesta = api_client.post(
        "/api/clasificar/",
        {"opiniones": ["falta modo oscuro", "la app se cierra sola"]},
        format="json",
    )

    assert respuesta.status_code == 200
    assert len(respuesta.data) == 2
    assert respuesta.data[0]["etiqueta"] == "RF"
    assert respuesta.data[0]["metodo"] == "zero_shot"
    assert respuesta.data[0]["texto_original"] == "falta modo oscuro"
    # ninguna clasificación se auto-aprueba: no se toca la base de datos
    assert Opinion.objects.count() == 0
    assert Requisito.objects.count() == 0


@pytest.mark.django_db
def test_clasificar_sin_lista_de_opiniones_devuelve_400(
    api_client, pipeline_falso, usuario_autenticado
):
    api_client.force_authenticate(usuario_autenticado)

    respuesta = api_client.post("/api/clasificar/", {"opiniones": []}, format="json")

    assert respuesta.status_code == 400
