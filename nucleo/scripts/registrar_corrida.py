"""Entrena, evalúa y registra una corrida de clasificador en `CorridaEvaluacion`.

Es el punto de unión entre el método (`nucleo/`, sin Django) y el panel de
métricas de la webapp (`webapp/apps/requisitos`, montado en `/evaluacion/`).
El entrenamiento y la evaluación son 100% de `nucleo/`; este script solo
añade la capa de persistencia en la base de datos para poder verlo en el
navegador. No sustituye a la bitácora (`docs/bitacora-experimentos.md`).

Uso (desde la raíz del repo, con el venv activo):
    python -m nucleo.scripts.registrar_corrida --metodo tfidf
    python -m nucleo.scripts.registrar_corrida --metodo semantico
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
GOLD_STANDARD_DEFECTO = RAIZ / "datos" / "gold_standard_privado" / "gold_standard_v1.csv"

COLUMNA_TEXTO = "texto_normalizado"
COLUMNA_ETIQUETA = "etiqueta_final"


def _preparar_django() -> None:
    sys.path.insert(0, str(RAIZ))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapp.config.settings")
    import django

    django.setup()


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Entrena+evalúa un clasificador sobre el gold standard y registra la corrida."
    )
    parser.add_argument("--metodo", choices=["tfidf", "semantico"], required=True)
    parser.add_argument("--entrada", type=Path, default=GOLD_STANDARD_DEFECTO)
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--tam-prueba", type=float, default=0.2)
    parser.add_argument(
        "--modelo-semantico",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    parser.add_argument("--notas", default="")
    args = parser.parse_args()

    _preparar_django()

    from nucleo.evaluacion.metricas import calcular_metricas
    from webapp.apps.requisitos.models import CorridaEvaluacion

    gold = pd.read_csv(args.entrada, encoding="utf-8-sig")
    gold[COLUMNA_TEXTO] = gold[COLUMNA_TEXTO].fillna("")
    textos = gold[COLUMNA_TEXTO].tolist()
    etiquetas = gold[COLUMNA_ETIQUETA].tolist()

    if args.metodo == "tfidf":
        from nucleo.clasificacion.tfidf_logreg import entrenar

        resultado = entrenar(textos, etiquetas, semilla=args.semilla, tam_prueba=args.tam_prueba)
        vectorizador = resultado["vectorizador"]
        X_test = vectorizador.transformar(resultado["textos_test"])
        modelo_embeddings = ""
        clasificador_nombre = "logreg"
    else:
        from nucleo.clasificacion.semantico_logreg import entrenar
        from nucleo.representacion.semantica import RepresentadorSemantico

        representador = RepresentadorSemantico(args.modelo_semantico, semilla=args.semilla)
        representador.cargar()
        resultado = entrenar(
            textos, etiquetas, representador, semilla=args.semilla, tam_prueba=args.tam_prueba
        )
        X_test = representador.transformar(resultado["textos_test"])
        modelo_embeddings = args.modelo_semantico
        clasificador_nombre = "logreg"

    y_pred = resultado["clasificador"].predict(X_test)
    metricas = calcular_metricas(resultado["y_test"], list(y_pred))

    corrida = CorridaEvaluacion.objects.create(
        metodo=args.metodo,
        modelo_embeddings=modelo_embeddings,
        clasificador=clasificador_nombre,
        hiperparametros={"class_weight": "balanced", "max_iter": 1000},
        semilla=args.semilla,
        tam_corpus=len(textos),
        dataset=args.entrada.stem,
        precision_global=metricas["precision_global"],
        recall_global=metricas["recall_global"],
        f1_global=metricas["f1_global"],
        metricas_por_clase=metricas["metricas_por_clase"],
        matriz_confusion=metricas["matriz_confusion"],
        notas=args.notas,
    )

    print(f"corrida #{corrida.pk} registrada: {corrida}")
    print(f"test: {len(resultado['textos_test'])} filas de {len(textos)} totales")


if __name__ == "__main__":
    _cli()
