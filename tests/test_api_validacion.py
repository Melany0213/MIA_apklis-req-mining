"""Pruebas de `GET /api/requisitos/` y `POST /api/requisitos/{id}/validar/`."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from webapp.apps.opiniones.models import Opinion
from webapp.apps.validacion.models import Requisito


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def usuario_autenticado(django_user_model):
    return django_user_model.objects.create_user(username="especialista", password="clave-segura-123")


@pytest.fixture
def requisito_propuesto(db):
    opinion = Opinion.objects.create(texto_original="falta modo oscuro")
    return Requisito.objects.create(
        opinion=opinion, etiqueta_propuesta="RF", confianza=0.7, metodo="zero_shot", estado="propuesto"
    )


@pytest.mark.django_db
def test_lista_requisitos_filtra_por_estado(api_client, requisito_propuesto):
    otra_opinion = Opinion.objects.create(texto_original="muy buena")
    Requisito.objects.create(
        opinion=otra_opinion, etiqueta_propuesta="Ruido", confianza=0.5,
        metodo="zero_shot", estado="validado", etiqueta_final="Ruido",
    )

    respuesta = api_client.get("/api/requisitos/", {"estado": "propuesto"})

    assert respuesta.status_code == 200
    assert len(respuesta.data) == 1
    assert respuesta.data[0]["id"] == requisito_propuesto.pk
    assert respuesta.data[0]["opinion"]["texto_original"] == "falta modo oscuro"


@pytest.mark.django_db
def test_validar_sin_login_no_autorizado(api_client, requisito_propuesto):
    respuesta = api_client.post(
        f"/api/requisitos/{requisito_propuesto.pk}/validar/", {"etiqueta_final": "RF"}, format="json"
    )

    assert respuesta.status_code in (401, 403)
    requisito_propuesto.refresh_from_db()
    assert requisito_propuesto.estado == "propuesto"


@pytest.mark.django_db
def test_validar_con_login_actualiza_el_requisito(api_client, usuario_autenticado, requisito_propuesto):
    api_client.force_authenticate(usuario_autenticado)

    respuesta = api_client.post(
        f"/api/requisitos/{requisito_propuesto.pk}/validar/",
        {"etiqueta_final": "RF", "notas": "confirmado"},
        format="json",
    )

    assert respuesta.status_code == 200
    requisito_propuesto.refresh_from_db()
    assert requisito_propuesto.estado == "validado"
    assert requisito_propuesto.etiqueta_final == "RF"
    assert requisito_propuesto.validado_por == usuario_autenticado
    assert requisito_propuesto.notas == "confirmado"
    assert requisito_propuesto.fecha_validacion is not None


@pytest.mark.django_db
def test_validar_con_etiqueta_invalida_devuelve_400(api_client, usuario_autenticado, requisito_propuesto):
    api_client.force_authenticate(usuario_autenticado)

    respuesta = api_client.post(
        f"/api/requisitos/{requisito_propuesto.pk}/validar/",
        {"etiqueta_final": "no-existe"},
        format="json",
    )

    assert respuesta.status_code == 400
    requisito_propuesto.refresh_from_db()
    assert requisito_propuesto.estado == "propuesto"
