"""Pruebas de la procedencia que acompaña a cada CSV exportado.

Estas pruebas existen por la limitación documentada en
`docs/ARQUITECTURA_ACTUAL.md` §7: el `texto_normalizado` del gold standard v1
se generó sin registrar con qué configuración, y eso no debe repetirse. Aquí
se fija el contrato del `.metadata.json`: qué campos lleva y que la huella del
DNJL cambia si el diccionario cambia.
"""

from __future__ import annotations

from pathlib import Path

from nucleo.preprocesamiento.lematizador import Lematizador
from nucleo.representacion.semantica import RepresentadorSemantico
from nucleo.scripts import exportar_propuestas


def _metadatos_de_prueba() -> dict:
    """Metadatos con valores fijos: ni `Lematizador` ni `RepresentadorSemantico`
    cargan el modelo en el constructor, así que no se toca disco ni la red."""
    return exportar_propuestas.construir_metadatos(
        argv=["exportar_propuestas.py", "--entrada", "corpus.csv"],
        entrada=Path("corpus.csv"),
        n_filas_entrada=10,
        n_filas_salida=8,
        lematizador=Lematizador("es_core_news_sm"),
        representador=RepresentadorSemantico("modelo/de-prueba"),
        semilla=42,
        commit_git="abc123",
    )


def test_metadatos_registran_la_configuracion_efectiva() -> None:
    metadatos = _metadatos_de_prueba()

    assert metadatos["modelo_spacy"] == "es_core_news_sm"
    assert metadatos["modelo_semantico"] == "modelo/de-prueba"
    assert metadatos["backend_semantico"] == "torch"
    assert metadatos["semilla"] == 42
    assert metadatos["commit_git"] == "abc123"
    assert metadatos["n_filas_entrada"] == 10
    assert metadatos["n_filas_salida"] == 8
    assert "--entrada" in metadatos["comando"]


def test_metadatos_no_pierden_ningun_campo_de_procedencia() -> None:
    """Si alguien quita un campo, la corrida deja de ser reproducible sin que
    nadie se entere — por eso el conjunto de claves es parte del contrato."""
    esperadas = {
        "fecha_hora",
        "comando",
        "commit_git",
        "entrada",
        "n_filas_entrada",
        "n_filas_salida",
        "modelo_spacy",
        "version_spacy",
        "modelo_semantico",
        "backend_semantico",
        "archivo_modelo_semantico",
        "semilla",
        "huella_dnjl",
    }

    assert set(_metadatos_de_prueba()) == esperadas


def test_huella_dnjl_es_determinista() -> None:
    assert exportar_propuestas._huella_dnjl() == exportar_propuestas._huella_dnjl()


def test_huella_dnjl_cambia_si_cambia_el_diccionario(monkeypatch) -> None:
    original = exportar_propuestas._huella_dnjl()
    monkeypatch.setattr(
        exportar_propuestas,
        "REGLAS_DNJL",
        {"NEOLOGISMOS_TECNOLOGICOS": {"termino_nuevo": "sustituto"}},
    )

    assert exportar_propuestas._huella_dnjl() != original


def test_commit_git_devuelve_hash_o_none() -> None:
    """No se asume que el entorno de test tenga git ni que sea un repo."""
    commit = exportar_propuestas._commit_git_actual()

    assert commit is None or (len(commit) == 40 and commit.isalnum())
