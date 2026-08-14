"""Pruebas del orquestador de fases 2-4 (`nucleo.pipeline.Pipeline`).

Usa dobles de prueba para el lematizador y los componentes de fase 3-4 (como
`tests/test_clasificacion_zero_shot.py` y `tests/test_subida_opiniones.py`)
para no cargar spaCy ni modelos de embeddings reales.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pytest

from nucleo.clasificacion.zero_shot import ClasificadorZeroShot
from nucleo.pipeline import Pipeline


class _LematizadorIdentidad:
    """Doble de prueba: no lematiza de verdad, devuelve el texto tal cual
    (así se puede comprobar que limpieza + DNJL sí se aplicaron, sin depender
    de un modelo real de spaCy)."""

    def lematizar(self, texto_limpio: str) -> str:
        return texto_limpio


class _RepresentadorSemanticoFalso:
    """Doble de prueba: embeddings fijos y conocidos por texto exacto."""

    _MAPA = {
        "pide funcion nueva": [1.0, 0.0],
        "se cierra sola siempre": [0.0, 1.0],
        "buena app": [-1.0, 0.0],
        "porque graciaas se cierra sola siempre": [0.0, 1.0],
    }

    def transformar(self, textos: list[str]) -> np.ndarray:
        return np.array([self._MAPA[texto] for texto in textos], dtype=np.float32)


class _VectorizadorPorLongitud:
    """Doble de prueba de un vectorizador/representador ya ajustado: la
    "representación" es simplemente la longitud del texto, para que el
    clasificador falso pueda decidir de forma determinista sin depender de
    TF-IDF ni embeddings reales."""

    def transformar(self, textos: list[str]) -> np.ndarray:
        return np.array([[float(len(t))] for t in textos], dtype=np.float32)


class _ClasificadorEntrenadoFalso:
    """Doble de prueba de un `LogisticRegression` ya entrenado: clasifica por
    longitud del texto (ver `_VectorizadorPorLongitud`) con `predict` y
    `predict_proba` deterministas, picklable a nivel de módulo para poder
    guardarlo con joblib como un modelo real."""

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.array(["RF" if fila[0] > 15 else "Ruido" for fila in X])

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return np.array(
            [[0.8, 0.1, 0.1] if fila[0] > 15 else [0.1, 0.1, 0.8] for fila in X]
        )


def _crear_zero_shot_falso(modelo_embeddings: str, semilla: int) -> ClasificadorZeroShot:
    prototipos = {
        "RF": ["pide funcion nueva"],
        "RNF": ["se cierra sola siempre"],
        "Ruido": ["buena app"],
    }
    return ClasificadorZeroShot(_RepresentadorSemanticoFalso(), prototipos=prototipos)


@pytest.fixture(autouse=True)
def _sin_spacy_real(monkeypatch):
    """Todas las pruebas de este módulo evitan cargar spaCy de verdad."""
    monkeypatch.setattr("nucleo.pipeline._crear_lematizador", lambda modelo: _LematizadorIdentidad())


def test_ejecuta_propuesta_zero_shot_por_defecto(monkeypatch) -> None:
    monkeypatch.setattr("nucleo.pipeline._crear_clasificador_zero_shot", _crear_zero_shot_falso)

    pipeline = Pipeline()
    pipeline.preparar()
    propuestas = pipeline.ejecutar(["pide funcion nueva"])

    assert len(propuestas) == 1
    assert propuestas[0].etiqueta == "RF"
    assert propuestas[0].metodo == "zero_shot"
    assert 0.0 < propuestas[0].confianza <= 1.0


def test_preprocesa_antes_de_clasificar(monkeypatch) -> None:
    """El texto que llega al clasificador ya pasó por limpieza + DNJL, aunque
    la lematización esté sustituida por un doble identidad."""
    monkeypatch.setattr("nucleo.pipeline._crear_clasificador_zero_shot", _crear_zero_shot_falso)

    pipeline = Pipeline()
    pipeline.preparar()
    (propuesta,) = pipeline.ejecutar(["xq graciaaaaas se cierra sola siempre"])

    # "xq" -> "porque" (DNJL) y "graciaaaaas" -> "graciaas" (colapso de repeticiones, limpieza)
    assert propuesta.texto_preprocesado == "porque graciaas se cierra sola siempre"
    assert propuesta.texto_original == "xq graciaaaaas se cierra sola siempre"


def test_ejecuta_con_modelo_tfidf_entrenado(tmp_path: Path) -> None:
    ruta_modelo = tmp_path / "tfidf_logreg.joblib"
    joblib.dump(
        {"vectorizador": _VectorizadorPorLongitud(), "clasificador": _ClasificadorEntrenadoFalso()},
        ruta_modelo,
    )

    pipeline = Pipeline(metodo="tfidf", ruta_modelo=ruta_modelo)
    pipeline.preparar()
    propuestas = pipeline.ejecutar(["corto", "un texto bastante mas largo que el anterior"])

    assert propuestas[0].etiqueta == "Ruido"  # texto corto -> longitud <= 15
    assert propuestas[1].etiqueta == "RF"  # texto largo -> longitud > 15
    assert all(p.metodo == "tfidf" for p in propuestas)
    assert propuestas[0].confianza == pytest.approx(0.8)


def test_ejecuta_con_modelo_semantico_entrenado_no_usa_zero_shot(tmp_path: Path) -> None:
    """Si se pasa `ruta_modelo`, debe usarse ese clasificador entrenado — no
    la propuesta zero-shot — incluso con metodo="semantico"."""
    ruta_modelo = tmp_path / "semantico_logreg.joblib"
    joblib.dump(
        {"representador": _VectorizadorPorLongitud(), "clasificador": _ClasificadorEntrenadoFalso()},
        ruta_modelo,
    )

    pipeline = Pipeline(metodo="semantico", ruta_modelo=ruta_modelo)
    pipeline.preparar()
    (propuesta,) = pipeline.ejecutar(["un texto bastante mas largo que el anterior"])

    assert propuesta.metodo == "semantico"
    assert propuesta.etiqueta == "RF"


def test_tfidf_sin_modelo_entrenado_lanza_error_claro() -> None:
    pipeline = Pipeline(metodo="tfidf")

    with pytest.raises(ValueError, match="ruta_modelo"):
        pipeline.preparar()


def test_ejecutar_sin_preparar_lanza_runtimeerror() -> None:
    pipeline = Pipeline()

    with pytest.raises(RuntimeError):
        pipeline.ejecutar(["hola"])
