"""Pruebas de entrenamiento TF-IDF + Regresión Logística (con datos sintéticos)."""

from __future__ import annotations

from nucleo.clasificacion.tfidf_logreg import entrenar


def _corpus_sintetico() -> tuple[list[str], list[str]]:
    textos = [
        "quiero que agreguen modo oscuro",
        "pedir que se pueda exportar a pdf",
        "sugerencia agregar boton de buscar",
        "falta una opcion para cambiar idioma",
        "la aplicacion se cierra sola siempre",
        "muy lento para descargar cualquier cosa",
        "consume demasiada bateria y datos",
        "no es seguro guardar la contrasena asi",
        "excelente aplicacion muy buena",
        "me encanta gracias",
        "buena app",
        "genial todo perfecto",
    ] * 3
    etiquetas = (
        ["RF", "RF", "RF", "RF", "RNF", "RNF", "RNF", "RNF", "Ruido", "Ruido", "Ruido", "Ruido"] * 3
    )
    return textos, etiquetas


def test_entrena_y_respeta_proporcion_train_test() -> None:
    textos, etiquetas = _corpus_sintetico()

    resultado = entrenar(textos, etiquetas, semilla=42, tam_prueba=0.25)

    total = len(textos)
    assert len(resultado["textos_train"]) + len(resultado["textos_test"]) == total
    assert len(resultado["textos_test"]) == round(total * 0.25)


def test_split_es_estratificado_por_clase() -> None:
    textos, etiquetas = _corpus_sintetico()

    resultado = entrenar(textos, etiquetas, semilla=42, tam_prueba=0.25)

    for clase in {"RF", "RNF", "Ruido"}:
        proporcion_original = etiquetas.count(clase) / len(etiquetas)
        proporcion_test = resultado["y_test"].count(clase) / len(resultado["y_test"])
        assert abs(proporcion_original - proporcion_test) < 0.15


def test_clasificador_entrenado_predice_las_tres_clases() -> None:
    textos, etiquetas = _corpus_sintetico()

    resultado = entrenar(textos, etiquetas, semilla=42, tam_prueba=0.25)

    assert set(resultado["clasificador"].classes_) == {"RF", "RNF", "Ruido"}

    X_test = resultado["vectorizador"].transformar(resultado["textos_test"])
    predicciones = resultado["clasificador"].predict(X_test)
    assert len(predicciones) == len(resultado["textos_test"])


def test_es_reproducible_con_la_misma_semilla() -> None:
    textos, etiquetas = _corpus_sintetico()

    resultado_1 = entrenar(textos, etiquetas, semilla=42, tam_prueba=0.25)
    resultado_2 = entrenar(textos, etiquetas, semilla=42, tam_prueba=0.25)

    assert resultado_1["textos_train"] == resultado_2["textos_train"]
    assert resultado_1["textos_test"] == resultado_2["textos_test"]
