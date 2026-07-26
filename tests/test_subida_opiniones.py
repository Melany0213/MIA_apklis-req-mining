"""Pruebas de la subida manual de opiniones (.csv / .json) desde la webapp.

Usa dobles de prueba para el lematizador y el clasificador (como
`test_clasificacion_zero_shot.py`) para no cargar spaCy ni el modelo de
embeddings reales: lo que se prueba es la vista, el parseo del archivo y
que las opiniones queden en la cola de validación, no el pipeline en sí
(ese ya tiene sus propias pruebas).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from webapp.apps.opiniones import pipeline
from webapp.apps.opiniones.models import Opinion
from webapp.apps.validacion.models import Requisito


class _LematizadorFalso:
    def lematizar(self, texto_limpio: str) -> str:
        return texto_limpio


class _ClasificadorFalso:
    def proponer(self, textos: list[str]) -> list[tuple[str, float]]:
        return [("RF", 0.9) for _ in textos]


@pytest.fixture
def componentes_falsos(monkeypatch):
    componentes = pipeline.ComponentesPipeline(_LematizadorFalso(), _ClasificadorFalso())
    monkeypatch.setattr("webapp.apps.opiniones.views.obtener_componentes", lambda: componentes)
    return componentes


@pytest.fixture
def cliente_autenticado(client, django_user_model):
    usuario = django_user_model.objects.create_user(username="analista", password="clave-segura-123")
    client.force_login(usuario)
    return client


@pytest.mark.django_db
def test_subida_csv_valida_crea_opiniones_propuestas(cliente_autenticado, componentes_falsos):
    contenido = (
        "texto,aplicacion\n"
        "la aplicacion se cierra sola al abrir la camara,Apklis\n"
        "seria bueno que agregaran modo oscuro,Apklis\n"
    ).encode("utf-8-sig")
    archivo = SimpleUploadedFile("opiniones.csv", contenido, content_type="text/csv")

    respuesta = cliente_autenticado.post(reverse("opiniones:subir"), {"archivo": archivo}, follow=True)

    assert respuesta.status_code == 200
    assert Opinion.objects.count() == 2
    assert Requisito.objects.filter(estado="propuesto").count() == 2


@pytest.mark.django_db
def test_subida_json_valida_crea_opiniones_propuestas(cliente_autenticado, componentes_falsos):
    contenido = (
        b'[{"texto": "la app consume demasiada bateria"}, '
        b'{"texto": "quisiera poder exportar mis datos a pdf"}]'
    )
    archivo = SimpleUploadedFile("opiniones.json", contenido, content_type="application/json")

    respuesta = cliente_autenticado.post(reverse("opiniones:subir"), {"archivo": archivo}, follow=True)

    assert respuesta.status_code == 200
    assert Opinion.objects.count() == 2
    assert Requisito.objects.filter(estado="propuesto").count() == 2


@pytest.mark.django_db
def test_subida_archivo_mal_formado_muestra_error_y_no_crea_nada(cliente_autenticado, componentes_falsos):
    contenido = b'{"texto": "falta cerrar el arreglo"'  # JSON corrupto
    archivo = SimpleUploadedFile("opiniones.json", contenido, content_type="application/json")

    respuesta = cliente_autenticado.post(reverse("opiniones:subir"), {"archivo": archivo}, follow=True)

    assert respuesta.status_code == 200
    mensajes = [str(m) for m in respuesta.context["messages"]]
    assert any("mal formado" in m for m in mensajes)
    assert Opinion.objects.count() == 0
    assert Requisito.objects.count() == 0


@pytest.mark.django_db
def test_subida_archivo_sin_columna_texto_muestra_error_y_no_crea_nada(
    cliente_autenticado, componentes_falsos
):
    contenido = "comentario,aplicacion\nme gusta la app,Apklis\n".encode("utf-8-sig")
    archivo = SimpleUploadedFile("opiniones.csv", contenido, content_type="text/csv")

    respuesta = cliente_autenticado.post(reverse("opiniones:subir"), {"archivo": archivo}, follow=True)

    assert respuesta.status_code == 200
    mensajes = [str(m) for m in respuesta.context["messages"]]
    assert any("texto" in m for m in mensajes)
    assert Opinion.objects.count() == 0
    assert Requisito.objects.count() == 0
