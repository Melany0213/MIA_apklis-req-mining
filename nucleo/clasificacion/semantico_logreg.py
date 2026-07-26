"""Clasificador semántico: embeddings (capa 3) + Regresión Logística (capa 4).

Es el componente central de la hipótesis de la tesis: su desempeño se
compara contra `nucleo.clasificacion.tfidf_logreg` sobre el **mismo** split
train/test del mismo gold standard (misma semilla, misma proporción, mismo
algoritmo de `train_test_split` aplicado en el mismo orden de filas) — de lo
contrario la comparación semántico vs. TF-IDF no sería válida.

Uso:
    python -m nucleo.clasificacion.semantico_logreg \
        --entrada datos/gold_standard_privado/gold_standard_v1.csv \
        --salida datos/modelos/semantico_logreg.joblib
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from nucleo.representacion.semantica import RepresentadorSemantico

COLUMNA_TEXTO = "texto_normalizado"
COLUMNA_ETIQUETA = "etiqueta_final"
SEMILLA_DEFECTO = 42
TAM_PRUEBA_DEFECTO = 0.2
MODELO_SEMANTICO_DEFECTO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def entrenar(
    textos: list[str],
    etiquetas: list[str],
    representador: RepresentadorSemantico,
    semilla: int = SEMILLA_DEFECTO,
    tam_prueba: float = TAM_PRUEBA_DEFECTO,
) -> dict[str, Any]:
    """Entrena embeddings semánticos + LogisticRegression.

    El split (`train_test_split` con los mismos argumentos: `indices`,
    `textos`, `etiquetas` en ese orden, mismo `test_size`, `random_state` y
    `stratify`) es intencionalmente idéntico al de
    `nucleo.clasificacion.tfidf_logreg.entrenar`, para que ambos enfoques se
    evalúen sobre exactamente las mismas filas de prueba. `indices_test` se
    devuelve explícitamente para poder verificarlo, no asumirlo.
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

    X_train = representador.transformar(textos_train)
    X_test = representador.transformar(textos_test)

    clasificador = LogisticRegression(
        class_weight="balanced",
        random_state=semilla,
        max_iter=1000,
    )
    clasificador.fit(X_train, y_train)

    return {
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
        description="Entrena embeddings semánticos + Regresión Logística sobre un gold standard."
    )
    parser.add_argument("--entrada", type=Path, required=True, help="CSV del gold standard")
    parser.add_argument(
        "--salida", type=Path, default=Path("datos/modelos/semantico_logreg.joblib")
    )
    parser.add_argument("--semilla", type=int, default=SEMILLA_DEFECTO)
    parser.add_argument("--tam-prueba", type=float, default=TAM_PRUEBA_DEFECTO)
    parser.add_argument("--modelo-semantico", default=MODELO_SEMANTICO_DEFECTO)
    parser.add_argument(
        "--backend",
        choices=["torch", "onnx"],
        default="torch",
        help="'onnx' permite usar --archivo-modelo con una variante cuantizada más liviana",
    )
    parser.add_argument(
        "--archivo-modelo",
        default=None,
        help="ruta del archivo .onnx dentro del repo (solo con --backend onnx)",
    )
    args = parser.parse_args()

    gold = pd.read_csv(args.entrada, encoding="utf-8-sig")
    gold[COLUMNA_TEXTO] = gold[COLUMNA_TEXTO].fillna("")

    representador = RepresentadorSemantico(
        args.modelo_semantico,
        semilla=args.semilla,
        backend=args.backend,
        archivo_modelo=args.archivo_modelo,
    )
    representador.cargar()

    resultado = entrenar(
        gold[COLUMNA_TEXTO].tolist(),
        gold[COLUMNA_ETIQUETA].tolist(),
        representador,
        semilla=args.semilla,
        tam_prueba=args.tam_prueba,
    )

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "representador": representador,
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
