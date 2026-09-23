"""El modelo de spaCy por defecto debe tener una única fuente de verdad.

`nucleo.preprocesamiento.lematizador.MODELO_DEFECTO` es esa fuente. Otros
puntos de entrada (el orquestador `nucleo.pipeline`, la configuración de la
webapp) deben *reexportarlo*, no declarar su propio valor por defecto. Este
es exactamente el bug de la Fase 0 de escalado (ver bitácora, entrada
2026-08-19): `pipeline.py` y `settings.py` declaraban por su
cuenta `"es_core_news_md"`, un modelo que nunca estuvo instalado en el
proyecto, y nada lo detectaba porque los tests evitaban cargar spaCy real.
Una anulación explícita (variable de entorno `MODELO_SPACY`, argumento
`--modelo-spacy` de un script, o el parámetro `modelo_spacy=` de `Pipeline`)
sigue siendo válida y no la cubre esta prueba: lo que no puede pasar es que
dos *defaults* de código diverjan en silencio.
"""

from __future__ import annotations

import os

from nucleo.pipeline import MODELO_SPACY_DEFECTO as DEFECTO_PIPELINE
from nucleo.preprocesamiento.lematizador import MODELO_DEFECTO as DEFECTO_LEMATIZADOR


def test_pipeline_reexporta_el_mismo_default_que_lematizador() -> None:
    assert DEFECTO_PIPELINE == DEFECTO_LEMATIZADOR


def test_settings_de_la_webapp_reexporta_el_mismo_default(monkeypatch) -> None:
    """Simula una instalación limpia (sin `MODELO_SPACY` en el entorno) y
    confirma que el default de `settings.py` cae en la misma fuente única,
    sin volver a evaluar el módulo Django completo (evita reimportar
    `webapp.config.settings`, que ya se cargó una vez por proceso de test)."""
    monkeypatch.delenv("MODELO_SPACY", raising=False)

    from decouple import config

    from webapp.config.settings import _MODELO_SPACY_DEFECTO

    assert _MODELO_SPACY_DEFECTO == DEFECTO_LEMATIZADOR
    # El propio valor con el que decouple resolvería MODELO_SPACY hoy, sin
    # override en el entorno, también debe coincidir.
    assert config("MODELO_SPACY", default=_MODELO_SPACY_DEFECTO) == DEFECTO_LEMATIZADOR


def test_env_local_no_diverge_del_default_sin_documentarlo() -> None:
    """Si hay un override real en el entorno (variable `MODELO_SPACY`, típicamente
    desde `.env`), debe ser exactamente el modelo instalado — no otro valor
    arbitrario que reintroduzca la misma clase de bug por otra vía."""
    valor_en_entorno = os.environ.get("MODELO_SPACY")
    if valor_en_entorno is not None:
        assert valor_en_entorno == DEFECTO_LEMATIZADOR, (
            f"MODELO_SPACY={valor_en_entorno!r} en el entorno difiere del único modelo "
            f"soportado ({DEFECTO_LEMATIZADOR!r}). Si es una anulación intencional, "
            "documéntala en .env.example y en la bitácora."
        )
