"""Pruebas de la fase 2 (preprocesamiento lingüístico)."""

from __future__ import annotations

import pytest

from nucleo.preprocesamiento import preprocesar
from nucleo.preprocesamiento.dnjl import normalizar_dnjl
from nucleo.preprocesamiento.lematizador import Lematizador
from nucleo.preprocesamiento.limpieza import limpiar_texto


def test_limpiar_texto_quita_url_y_mencion() -> None:
    texto = "mira esto https://apklis.cu/app/foo @usuario buenisima app"
    resultado = limpiar_texto(texto)
    assert "http" not in resultado
    assert "@usuario" not in resultado
    assert "buenisima app" in resultado


def test_limpiar_texto_colapsa_repeticiones() -> None:
    assert limpiar_texto("graciaaaaas") == "graciaas"
    assert limpiar_texto("jajajajaja") == "jaja"


def test_limpiar_texto_normaliza_espacios() -> None:
    assert limpiar_texto("  hola   mundo  ") == "hola mundo"


def test_limpiar_texto_conserva_emoji() -> None:
    assert "😀" in limpiar_texto("me encanta 😀")


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        # Categoría 1 — Neologismos tecnológicos y jerga
        ("pincha", "funciona"),
        ("funde", "agota"),
        ("lag", "retraso"),
        ("crashea", "falla"),
        # Categoría 2 — Abreviaturas informales
        ("xq", "porque"),
        ("q", "que"),
        ("d", "de"),
        ("x", "por"),
        # Categoría 3 — Errores fonético-ortográficos
        ("aser", "hacer"),
        ("habrir", "abrir"),
        ("bota", "vota"),
        ("movil", "móvil"),
        # Categoría 4 — Lematización de verbos
        ("actualizando", "actualizar"),
        ("actualicé", "actualizar"),
        ("actualiza", "actualizar"),
    ],
)
def test_normalizar_dnjl_tabla_7(entrada: str, esperado: str) -> None:
    assert normalizar_dnjl(entrada) == esperado


def test_normalizar_dnjl_respeta_limites_de_palabra() -> None:
    # "x" no debe sustituirse dentro de otra palabra ni de un token no relacionado
    assert normalizar_dnjl("excelente") == "excelente"
    assert normalizar_dnjl("máximo") == "máximo"


def test_normalizar_dnjl_es_insensible_a_mayusculas() -> None:
    assert normalizar_dnjl("XQ no Pincha") == "porque no funciona"


def test_normalizar_dnjl_en_frase_completa() -> None:
    resultado = normalizar_dnjl("no aser nada xq la app se funde y va con lag")
    assert resultado == "no hacer nada porque la app se agota y va con retraso"


def test_normalizar_dnjl_no_afecta_texto_sin_jerga() -> None:
    assert normalizar_dnjl("la aplicación funciona muy bien") == "la aplicación funciona muy bien"


@pytest.fixture(scope="module")
def lematizador() -> Lematizador:
    lem = Lematizador()
    lem.cargar()
    return lem


def test_lematizador_reduce_a_forma_base(lematizador: Lematizador) -> None:
    resultado = lematizador.lematizar("las aplicaciones se cerraban solas")
    assert "aplicacion" in resultado or "aplicación" in resultado
    assert "cerraban" not in resultado


def test_lematizador_falla_sin_cargar() -> None:
    with pytest.raises(RuntimeError):
        Lematizador().lematizar("hola")


def test_preprocesar_encadena_limpieza_y_lematizacion(lematizador: Lematizador) -> None:
    resultado = preprocesar("La aplicacioooon @pepe https://x.co es buenisimaaaa!!!", lematizador)
    assert "@pepe" not in resultado
    assert "http" not in resultado
    assert resultado == resultado.lower()
