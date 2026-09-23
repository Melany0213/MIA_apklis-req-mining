"""Prueba de humo del clasificador zero-shot con el modelo de embeddings real.

A diferencia de `tests/test_clasificacion_zero_shot.py` (que usa un doble de
prueba con vectores conocidos para probar la lógica de decisión de forma
rápida y determinista), este módulo carga el modelo real
(`RepresentadorSemantico` + `PROTOTIPOS` de producción) para confirmar que la
configuración *tal como está desplegada* clasifica correctamente ejemplos
inequívocos de cada clase. Requiere el modelo descargado localmente (ver
`nucleo/representacion/semantica.py`); si no está cacheado, `cargar()` lo
descarga de Hugging Face antes de continuar sin conexión.
"""

from __future__ import annotations

import pytest

from nucleo.clasificacion.zero_shot import PROTOTIPOS, ClasificadorZeroShot
from nucleo.representacion.semantica import RepresentadorSemantico

MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

pytestmark = pytest.mark.modelo_real


@pytest.fixture(scope="module")
def clasificador() -> ClasificadorZeroShot:
    representador = RepresentadorSemantico(MODELO, semilla=42)
    representador.cargar()
    return ClasificadorZeroShot(representador, prototipos=PROTOTIPOS)


@pytest.mark.parametrize(
    "texto, etiqueta_esperada",
    [
        ("falta una opcion para cambiar el idioma de la aplicacion", "RF"),
        ("porfavor agreguen un buscador dentro de la app, no hay forma de buscar nada", "RF"),
        ("la aplicacion se cierra sola todo el tiempo y hay que volver a abrirla", "RNF"),
        ("consume demasiada bateria y datos moviles solo con tenerla abierta", "RNF"),
        ("genial, todo perfecto, siganla asi", "Ruido"),
        ("buenas tardes a todos", "Ruido"),
    ],
)
def test_clasificador_zero_shot_predice_la_clase_esperada(
    clasificador: ClasificadorZeroShot, texto: str, etiqueta_esperada: str
) -> None:
    (etiqueta, confianza), = clasificador.proponer([texto])
    assert etiqueta == etiqueta_esperada
    assert 0.0 < confianza <= 1.0
