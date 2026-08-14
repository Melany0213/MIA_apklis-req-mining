"""Pruebas de descartar una opinión no aprovechable como requisito (fase 5).

Sigue el patrón de `tests/test_subida_opiniones.py`: cliente de pruebas de
Django, `@pytest.mark.django_db`, sin dobles de PLN porque esta vista no toca
el pipeline de clasificación, solo el estado de un `Requisito` ya existente.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from webapp.apps.opiniones.models import Opinion
from webapp.apps.validacion.models import Requisito


@pytest.fixture
def cliente_autenticado(client, django_user_model):
    usuario = django_user_model.objects.create_user(username="especialista", password="clave-segura-123")
    client.force_login(usuario)
    return client, usuario


@pytest.fixture
def requisito_propuesto(db):
    opinion = Opinion.objects.create(texto_original="publicidad de otra cosa, nada que ver con la app")
    return Requisito.objects.create(
        opinion=opinion, etiqueta_propuesta="Ruido", confianza=0.4, metodo="zero_shot", estado="propuesto"
    )


@pytest.mark.django_db
def test_descartar_sin_login_no_modifica_el_requisito(client, requisito_propuesto):
    respuesta = client.post(reverse("validacion:descartar", args=[requisito_propuesto.pk]))

    assert respuesta.status_code == 302
    assert "/admin/login/" in respuesta.url
    requisito_propuesto.refresh_from_db()
    assert requisito_propuesto.estado == "propuesto"


@pytest.mark.django_db
def test_descartar_marca_estado_sin_asignar_etiqueta_final(cliente_autenticado, requisito_propuesto):
    cliente, usuario = cliente_autenticado

    respuesta = cliente.post(
        reverse("validacion:descartar", args=[requisito_propuesto.pk]),
        {"notas": "spam, no relacionado con la app"},
    )

    assert respuesta.status_code == 302
    requisito_propuesto.refresh_from_db()
    assert requisito_propuesto.estado == "descartado"
    assert requisito_propuesto.etiqueta_final == ""
    assert requisito_propuesto.validado_por == usuario
    assert requisito_propuesto.fecha_validacion is not None
    assert requisito_propuesto.notas == "spam, no relacionado con la app"


@pytest.mark.django_db
def test_descartar_saca_de_la_cola_de_propuestos_y_entra_en_descartados(
    cliente_autenticado, requisito_propuesto
):
    cliente, _ = cliente_autenticado

    cliente.post(reverse("validacion:descartar", args=[requisito_propuesto.pk]), {"notas": ""})

    cola_propuestos = cliente.get(reverse("validacion:cola"), {"estado": "propuesto"})
    cola_descartados = cliente.get(reverse("validacion:cola"), {"estado": "descartado"})

    assert requisito_propuesto not in cola_propuestos.context["requisitos"]
    assert list(cola_descartados.context["requisitos"]) == [requisito_propuesto]
    assert cola_descartados.context["total_descartado"] == 1
