"""Pruebas de la fase 1 (extracción de Apklis) sin llamadas de red reales."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nucleo.extraccion.anonimizacion import anonimizar_autor
from nucleo.extraccion.apklis import URL_BASE, ClienteApklis
from nucleo.extraccion.corpus import construir_corpus, guardar_csv


class _RespuestaFalsa:
    """Doble de prueba para `requests.Response`."""

    def __init__(self, cuerpo: dict) -> None:
        self._cuerpo = cuerpo

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._cuerpo


def _reseña(usuario: str, comentario: str, aplicacion: str = "cu.todus.android") -> dict:
    return {
        "user": {"username": usuario, "first_name": "X", "last_name": "Y"},
        "comment": comentario,
        "rating": 5,
        "published": "2026-06-24T21:04:53.798903+00:00",
        "public": True,
        "application": aplicacion,
        "version": "v2.1.2",
        "replies": [],
    }


def _sesion_paginada(paginas: list[dict]) -> MagicMock:
    """Simula una sesión requests cuyo .get() devuelve cada página en orden."""
    sesion = MagicMock()
    sesion.headers = {}
    respuestas = [_RespuestaFalsa(p) for p in paginas]
    sesion.get.side_effect = respuestas
    return sesion


def test_paginar_sigue_el_campo_next_sin_repetir_parametros() -> None:
    pagina1 = {
        "results": [_reseña("ana", "buena app")],
        "next": f"{URL_BASE}v2/review/?application=x&limit=1&offset=1&public=true",
    }
    pagina2 = {"results": [_reseña("beto", "se cierra sola")], "next": None}
    sesion = _sesion_paginada([pagina1, pagina2])

    cliente = ClienteApklis(sesion=sesion, espera_entre_peticiones=0)
    resultados = list(cliente.listar_opiniones("cu.todus.android"))

    assert len(resultados) == 2
    assert sesion.get.call_count == 2
    primera_llamada = sesion.get.call_args_list[0]
    assert primera_llamada.kwargs["params"] == {
        "application": "cu.todus.android", "public": "true", "limit": 100,
    }
    segunda_llamada = sesion.get.call_args_list[1]
    assert segunda_llamada.kwargs["params"] is None  # el next ya trae los parámetros


def test_listar_opiniones_filtra_solo_publicas_por_defecto() -> None:
    sesion = _sesion_paginada([{"results": [], "next": None}])
    cliente = ClienteApklis(sesion=sesion, espera_entre_peticiones=0)

    list(cliente.listar_opiniones("cu.todus.android"))

    params = sesion.get.call_args_list[0].kwargs["params"]
    assert params == {"application": "cu.todus.android", "public": "true", "limit": 100}


def test_anonimizar_autor_es_consistente_y_no_reversible_a_ojo() -> None:
    hash1 = anonimizar_autor("mateo123")
    hash2 = anonimizar_autor("mateo123")
    hash_otro = anonimizar_autor("otro_usuario")

    assert hash1 == hash2
    assert hash1 != hash_otro
    assert "mateo123" not in hash1


def test_construir_corpus_anonimiza_y_descarta_comentarios_vacios() -> None:
    pagina = {
        "results": [
            _reseña("mateo123", "  la app se traba al subir fotos  "),
            _reseña("otro", "   "),  # comentario vacío tras strip -> se descarta
        ],
        "next": None,
    }
    sesion = _sesion_paginada([pagina])
    cliente = ClienteApklis(sesion=sesion, espera_entre_peticiones=0)

    opiniones = construir_corpus(cliente, "cu.todus.android")

    assert len(opiniones) == 1
    opinion = opiniones[0]
    assert opinion.texto == "la app se traba al subir fotos"
    assert opinion.id_autor_anonimo == anonimizar_autor("mateo123")
    assert opinion.aplicacion == "cu.todus.android"
    assert opinion.fuente == "apklis"


def test_construir_corpus_respeta_el_limite() -> None:
    pagina = {
        "results": [_reseña(f"user{i}", f"comentario {i}") for i in range(5)],
        "next": None,
    }
    sesion = _sesion_paginada([pagina])
    cliente = ClienteApklis(sesion=sesion, espera_entre_peticiones=0)

    opiniones = construir_corpus(cliente, "cu.todus.android", limite=2)

    assert len(opiniones) == 2


def test_guardar_csv_escribe_encabezado_y_filas(tmp_path: Path) -> None:
    pagina = {"results": [_reseña("mateo123", "excelente aplicacion")], "next": None}
    sesion = _sesion_paginada([pagina])
    cliente = ClienteApklis(sesion=sesion, espera_entre_peticiones=0)
    opiniones = construir_corpus(cliente, "cu.todus.android")

    ruta = tmp_path / "corpus_crudo" / "todus.csv"
    guardar_csv(opiniones, ruta)

    contenido = ruta.read_text(encoding="utf-8")
    assert "id_autor_anonimo" in contenido.splitlines()[0]
    assert "excelente aplicacion" in contenido
    assert "mateo123" not in contenido


@pytest.mark.parametrize("username_vacio", ["", None])
def test_opinion_sin_usuario_queda_marcada_como_anonimo(username_vacio) -> None:
    reseña = _reseña("x", "buena")
    reseña["user"]["username"] = username_vacio
    pagina = {"results": [reseña], "next": None}
    sesion = _sesion_paginada([pagina])
    cliente = ClienteApklis(sesion=sesion, espera_entre_peticiones=0)

    opiniones = construir_corpus(cliente, "cu.todus.android")

    assert opiniones[0].id_autor_anonimo == "anonimo"
