"""Prueba de humo de `Pipeline` con spaCy y el modelo de embeddings reales.

A diferencia de `tests/test_pipeline.py` (dobles de prueba para lematizador y
clasificador, rápido y determinista), este módulo NO monkeypatchea nada: es
la única prueba que instancia `Pipeline()` con su configuración por defecto
tal cual la usaría cualquier punto de entrada real. Existe para que un
`OSError [E050]` (modelo de spaCy no instalado, ver Fase 0 en la bitácora —
`pipeline.py` llegó a tener un default que nunca se pudo cargar en este
entorno y nadie lo notó porque los tests lo evitaban con dobles) no vuelva a
pasar inadvertido. Se puede excluir puntualmente con
`pytest -m "not modelo_real"`, pero debe correr en CI por defecto.
"""

from __future__ import annotations

import pytest

from nucleo.pipeline import Pipeline

pytestmark = pytest.mark.modelo_real


def test_pipeline_por_defecto_procesa_de_extremo_a_extremo() -> None:
    pipeline = Pipeline()
    pipeline.preparar()

    (propuesta,) = pipeline.ejecutar(["la aplicacion se cierra sola todo el tiempo"])

    assert propuesta.etiqueta in {"RF", "RNF", "Ruido"}
    assert propuesta.metodo == "zero_shot"
    assert propuesta.texto_preprocesado != ""
    assert 0.0 < propuesta.confianza <= 1.0
