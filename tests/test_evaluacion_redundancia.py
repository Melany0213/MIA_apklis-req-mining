"""Pruebas de la medición de redundancia del catálogo de candidatos (datos sintéticos)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from nucleo.evaluacion.redundancia import (
    barrer_umbrales,
    cargar_candidatos,
    construir_tabla_comparativa,
    evaluar_contra_manual,
    exportar_grupos,
    matriz_similitud_coseno,
)


def test_cargar_candidatos_filtra_solo_rf_y_rnf(tmp_path: Path) -> None:
    gold = pd.DataFrame(
        {
            "texto_original": ["a", "b", "c", "d"],
            "texto_normalizado": ["a", "b", "c", "d"],
            "etiqueta_final": ["RF", "Ruido", "RNF", "Ruido"],
        }
    )
    ruta = tmp_path / "gold.csv"
    gold.to_csv(ruta, index=False)

    candidatos = cargar_candidatos(ruta)

    assert len(candidatos) == 2
    assert set(candidatos["etiqueta_final"]) == {"RF", "RNF"}
    assert candidatos["id_opinion"].tolist() == [0, 2]


def test_barrer_umbrales_mas_alto_nunca_produce_mas_grupos() -> None:
    vectores = np.array(
        [
            [1.0, 0.0],
            [0.99, 0.05],
            [0.0, 1.0],
            [-1.0, 0.0],
        ],
        dtype=np.float32,
    )

    tabla, etiquetas_por_umbral = barrer_umbrales(vectores, [0.1, 0.5])

    assert list(tabla["umbral"]) == [0.1, 0.5]
    assert tabla.loc[tabla["umbral"] == 0.5, "grupos"].item() <= tabla.loc[tabla["umbral"] == 0.1, "grupos"].item()
    assert set(etiquetas_por_umbral.keys()) == {0.1, 0.5}


def test_tasa_redundancia_es_uno_menos_grupos_entre_total() -> None:
    vectores = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]], dtype=np.float32)

    tabla, _ = barrer_umbrales(vectores, [0.3])

    fila = tabla.iloc[0]
    assert fila["tasa_redundancia"] == round(1 - fila["grupos"] / 4, 4)


def test_matriz_similitud_coseno_es_simetrica_y_diagonal_uno() -> None:
    vectores = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32)

    sim = matriz_similitud_coseno(vectores)

    assert np.allclose(np.diag(sim), 1.0)
    assert np.allclose(sim, sim.T)


def test_construir_tabla_comparativa_combina_por_umbral() -> None:
    tabla_tfidf = pd.DataFrame({"umbral": [0.1, 0.2], "grupos": [4, 3], "tasa_redundancia": [0.0, 0.25]})
    tabla_semantico = pd.DataFrame({"umbral": [0.1, 0.2], "grupos": [3, 2], "tasa_redundancia": [0.25, 0.5]})

    combinada = construir_tabla_comparativa(tabla_tfidf, tabla_semantico)

    assert list(combinada.columns) == ["umbral", "grupos_tfidf", "tasa_tfidf", "grupos_semantico", "tasa_semantico"]
    assert combinada["grupos_tfidf"].tolist() == [4, 3]
    assert combinada["grupos_semantico"].tolist() == [3, 2]


def test_exportar_grupos_escribe_cada_opinion_en_su_grupo(tmp_path: Path) -> None:
    candidatos = pd.DataFrame(
        {
            "id_opinion": [0, 1, 2],
            "texto_original": ["quiero modo oscuro", "pido modo oscuro", "se cierra sola"],
        }
    )
    etiquetas = np.array([0, 0, 1])
    ruta_salida = tmp_path / "grupos.txt"

    exportar_grupos(candidatos, etiquetas, ruta_salida)

    contenido = ruta_salida.read_text(encoding="utf-8")
    assert "quiero modo oscuro" in contenido
    assert "pido modo oscuro" in contenido
    assert "se cierra sola" in contenido
    assert contenido.count("=== Grupo") == 2


def test_evaluar_contra_manual_ari_perfecto_cuando_coincide(tmp_path: Path) -> None:
    candidatos = pd.DataFrame({"id_opinion": [0, 1, 2, 3]})
    etiquetas_auto = np.array([0, 0, 1, 1])
    manual = pd.DataFrame({"id_opinion": [0, 1, 2, 3], "id_grupo": ["a", "a", "b", "b"]})
    ruta_manual = tmp_path / "manual.csv"
    manual.to_csv(ruta_manual, index=False)

    resultado = evaluar_contra_manual(candidatos, etiquetas_auto, ruta_manual)

    assert resultado["ari"] == 1.0
    assert resultado["homogeneidad"] == 1.0
    assert resultado["completitud"] == 1.0
    assert resultado["n_comparadas"] == 4


def test_evaluar_contra_manual_usa_solo_el_subconjunto_en_comun(tmp_path: Path) -> None:
    candidatos = pd.DataFrame({"id_opinion": [0, 1, 2, 3]})
    etiquetas_auto = np.array([0, 0, 1, 1])
    manual = pd.DataFrame({"id_opinion": [0, 1], "id_grupo": ["a", "a"]})
    ruta_manual = tmp_path / "manual.csv"
    manual.to_csv(ruta_manual, index=False)

    resultado = evaluar_contra_manual(candidatos, etiquetas_auto, ruta_manual)

    assert resultado["n_comparadas"] == 2
