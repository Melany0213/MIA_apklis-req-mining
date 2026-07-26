"""Clasificador de línea base: TF-IDF (capa 3) + Regresión Logística (capa 4).

Entrena sobre el gold standard validado en la fase 5 (ver
`nucleo.evaluacion.muestra_validacion` y la bitácora del 2026-07-04). Es la
línea base de frecuencia de palabras contra la que la tesis compara la
representación semántica contextual (hipótesis central, Tabla 4).

Uso:
    python -m nucleo.clasificacion.tfidf_logreg \
        --entrada datos/gold_standard_privado/gold_standard_v1.csv \
        --salida datos/modelos/tfidf_logreg.joblib
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from nucleo.representacion.tfidf import RepresentadorTFIDF

COLUMNA_TEXTO = "texto_normalizado"
COLUMNA_ETIQUETA = "etiqueta_final"
SEMILLA_DEFECTO = 42
TAM_PRUEBA_DEFECTO = 0.2


def entrenar(
    textos: list[str],
    etiquetas: list[str],
    semilla: int = SEMILLA_DEFECTO,
    tam_prueba: float = TAM_PRUEBA_DEFECTO,
) -> dict[str, Any]:
    """Entrena TF-IDF + LogisticRegression con split estratificado train/test.

    `class_weight="balanced"` compensa el desbalance del gold standard
    (Ruido/RNF/RF muy dispares): sin esto, el clasificador tendería a
    predecir casi siempre la clase mayoritaria.
    """
    indices = list(range(len(textos)))
    indices_train, indices_test, textos_train, textos_test, y_train, y_test = train_test_split(
        indices,
        textos,
        etiquetas,
        test_size=tam_prueba,
        random_state=semilla,
        stratify=etiquetas,
    )

    vectorizador = RepresentadorTFIDF()
    X_train = vectorizador.ajustar_transformar(textos_train)
    X_test = vectorizador.transformar(textos_test)

    clasificador = LogisticRegression(
        class_weight="balanced",
        random_state=semilla,
        max_iter=1000,
    )
    clasificador.fit(X_train, y_train)

    return {
        "vectorizador": vectorizador,
        "clasificador": clasificador,
        "semilla": semilla,
        "tam_prueba": tam_prueba,
        "indices_train": indices_train,
        "indices_test": indices_test,
        "textos_train": textos_train,
        "textos_test": textos_test,
        "y_train": y_train,
        "y_test": y_test,
    }


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Entrena TF-IDF + Regresión Logística sobre un gold standard."
    )
    parser.add_argument("--entrada", type=Path, required=True, help="CSV del gold standard")
    parser.add_argument(
        "--salida", type=Path, default=Path("datos/modelos/tfidf_logreg.joblib")
    )
    parser.add_argument("--semilla", type=int, default=SEMILLA_DEFECTO)
    parser.add_argument("--tam-prueba", type=float, default=TAM_PRUEBA_DEFECTO)
    args = parser.parse_args()

    gold = pd.read_csv(args.entrada, encoding="utf-8-sig")
    gold[COLUMNA_TEXTO] = gold[COLUMNA_TEXTO].fillna("")
    resultado = entrenar(
        gold[COLUMNA_TEXTO].tolist(),
        gold[COLUMNA_ETIQUETA].tolist(),
        semilla=args.semilla,
        tam_prueba=args.tam_prueba,
    )

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "vectorizador": resultado["vectorizador"],
            "clasificador": resultado["clasificador"],
            "semilla": resultado["semilla"],
            "tam_prueba": resultado["tam_prueba"],
        },
        args.salida,
    )

    print(f"train: {len(resultado['textos_train'])} filas")
    print(f"test: {len(resultado['textos_test'])} filas")
    print(f"modelo guardado en {args.salida}")


if __name__ == "__main__":
    _cli()
