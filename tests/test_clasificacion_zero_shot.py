"""Pruebas de la propuesta zero-shot (sin cargar el modelo real de embeddings)."""

from __future__ import annotations

import numpy as np

from nucleo.clasificacion.zero_shot import ClasificadorZeroShot


class _RepresentadorFalso:
    """Doble de prueba: devuelve embeddings fijos conocidos por texto."""

    def __init__(self, mapa: dict[str, list[float]]) -> None:
        self._mapa = mapa

    def transformar(self, textos: list[str]) -> np.ndarray:
        return np.array([self._mapa[texto] for texto in textos], dtype=np.float32)


def test_elige_la_clase_mas_similar_al_prototipo() -> None:
    prototipos = {"RF": ["pide funcion"], "RNF": ["se cierra"], "Ruido": ["buena app"]}
    mapa = {
        "pide funcion": [1.0, 0.0],
        "se cierra": [0.0, 1.0],
        "buena app": [-1.0, 0.0],
        "quiero que agreguen modo oscuro": [0.9, 0.1],
    }
    clasificador = ClasificadorZeroShot(_RepresentadorFalso(mapa), prototipos=prototipos)

    (etiqueta, confianza), = clasificador.proponer(["quiero que agreguen modo oscuro"])

    assert etiqueta == "RF"
    assert 0.0 < confianza <= 1.0


def test_confianza_es_mas_alta_cuando_la_clase_ganadora_es_inequivoca() -> None:
    prototipos = {"RF": ["pide funcion"], "RNF": ["se cierra"], "Ruido": ["buena app"]}
    mapa = {
        "pide funcion": [1.0, 0.0],
        "se cierra": [0.0, 1.0],
        "buena app": [-1.0, 0.0],
        "muy claro": [1.0, 0.0],
        "ambiguo": [0.5, 0.5],
    }
    clasificador = ClasificadorZeroShot(_RepresentadorFalso(mapa), prototipos=prototipos)

    (_, confianza_clara), (_, confianza_ambigua) = clasificador.proponer(["muy claro", "ambiguo"])

    assert confianza_clara > confianza_ambigua
