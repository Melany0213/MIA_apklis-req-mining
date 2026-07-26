"""Pruebas de entrenamiento embeddings + Regresión Logística (con datos sintéticos)."""

from __future__ import annotations

import numpy as np

from nucleo.clasificacion import tfidf_logreg
from nucleo.clasificacion.semantico_logreg import entrenar


class _RepresentadorFalso:
    """Doble de prueba: no carga ningún modelo, devuelve embeddings fijos conocidos."""

    _MAPA = {
        "quiero que agreguen modo oscuro": [1.0, 0.0],
        "pedir que se pueda exportar a pdf": [0.9, 0.1],
        "sugerencia agregar boton de buscar": [0.8, 0.2],
        "falta una opcion para cambiar idioma": [0.85, 0.05],
        "la aplicacion se cierra sola siempre": [0.0, 1.0],
        "muy lento para descargar cualquier cosa": [-0.1, 0.9],
        "consume demasiada bateria y datos": [0.1, 0.8],
        "no es seguro guardar la contrasena asi": [-0.2, 1.0],
        "excelente aplicacion muy buena": [-1.0, 0.0],
        "me encanta gracias": [-0.9, -0.1],
        "buena app": [-0.8, 0.1],
        "genial todo perfecto": [-1.0, -0.2],
    }

    def transformar(self, textos: list[str]) -> np.ndarray:
        return np.array([self._MAPA[texto] for texto in textos], dtype=np.float32)


def _corpus_sintetico() -> tuple[list[str], list[str]]:
    textos = list(_RepresentadorFalso._MAPA.keys()) * 3
    etiquetas = (
        ["RF", "RF", "RF", "RF", "RNF", "RNF", "RNF", "RNF", "Ruido", "Ruido", "Ruido", "Ruido"] * 3
    )
    return textos, etiquetas


def test_entrena_y_respeta_proporcion_train_test() -> None:
    textos, etiquetas = _corpus_sintetico()

    resultado = entrenar(textos, etiquetas, _RepresentadorFalso(), semilla=42, tam_prueba=0.25)

    total = len(textos)
    assert len(resultado["textos_train"]) + len(resultado["textos_test"]) == total
    assert len(resultado["textos_test"]) == round(total * 0.25)


def test_split_es_estratificado_por_clase() -> None:
    textos, etiquetas = _corpus_sintetico()

    resultado = entrenar(textos, etiquetas, _RepresentadorFalso(), semilla=42, tam_prueba=0.25)

    for clase in {"RF", "RNF", "Ruido"}:
        proporcion_original = etiquetas.count(clase) / len(etiquetas)
        proporcion_test = resultado["y_test"].count(clase) / len(resultado["y_test"])
        assert abs(proporcion_original - proporcion_test) < 0.15


def test_clasificador_entrenado_predice_las_tres_clases() -> None:
    textos, etiquetas = _corpus_sintetico()

    resultado = entrenar(textos, etiquetas, _RepresentadorFalso(), semilla=42, tam_prueba=0.25)

    assert set(resultado["clasificador"].classes_) == {"RF", "RNF", "Ruido"}

    X_test = _RepresentadorFalso().transformar(resultado["textos_test"])
    predicciones = resultado["clasificador"].predict(X_test)
    assert len(predicciones) == len(resultado["textos_test"])


def test_es_reproducible_con_la_misma_semilla() -> None:
    textos, etiquetas = _corpus_sintetico()

    resultado_1 = entrenar(textos, etiquetas, _RepresentadorFalso(), semilla=42, tam_prueba=0.25)
    resultado_2 = entrenar(textos, etiquetas, _RepresentadorFalso(), semilla=42, tam_prueba=0.25)

    assert resultado_1["indices_test"] == resultado_2["indices_test"]
    assert resultado_1["textos_train"] == resultado_2["textos_train"]
    assert resultado_1["textos_test"] == resultado_2["textos_test"]


def test_mismo_split_exacto_que_tfidf_logreg() -> None:
    """Crítico para la validez de la comparación: ambos módulos deben evaluar
    sobre las mismas filas de prueba (mismos índices), no solo la misma
    proporción o la misma semilla nominal."""
    textos, etiquetas = _corpus_sintetico()

    resultado_tfidf = tfidf_logreg.entrenar(textos, etiquetas, semilla=42, tam_prueba=0.25)
    resultado_semantico = entrenar(textos, etiquetas, _RepresentadorFalso(), semilla=42, tam_prueba=0.25)

    assert resultado_tfidf["indices_test"] == resultado_semantico["indices_test"]
    assert resultado_tfidf["indices_train"] == resultado_semantico["indices_train"]
    assert resultado_tfidf["y_test"] == resultado_semantico["y_test"]
