"""Experimento principal de la tesis: semántico vs. TF-IDF sobre el gold standard.

Entrena y evalúa, sobre el **mismo** split train/test del gold standard
(`nucleo.clasificacion.tfidf_logreg` y `nucleo.clasificacion.semantico_logreg`
comparten literalmente el mismo `train_test_split`, ver docstring de ese
módulo), los dos enfoques que compara la hipótesis de la tesis:

- TF-IDF + Regresión Logística (línea base).
- Embeddings semánticos + Regresión Logística (método propuesto).

Además mide la tasa de redundancia de cada representación sobre los
candidatos RF/RNF, reutilizando `nucleo.evaluacion.redundancia` en el umbral
operativo ya justificado en `docs/bitacora-experimentos.md` (0.30).

Requiere el gold standard local (`datos/gold_standard_privado/gold_standard_v1.csv`):
no se versiona por privacidad (ver `.gitignore`), así que este script solo
puede correr donde ese archivo exista — no genera ni inventa datos si falta.

Uso:
    python scripts/baseline.py
    python scripts/baseline.py --semilla 42 --tam-prueba 0.2
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from nucleo.clasificacion import semantico_logreg, tfidf_logreg  # noqa: E402
from nucleo.evaluacion.metricas import calcular_metricas  # noqa: E402
from nucleo.evaluacion.redundancia import cargar_candidatos, barrer_umbrales  # noqa: E402
from nucleo.representacion.semantica import RepresentadorSemantico  # noqa: E402

GOLD_STANDARD_DEFECTO = RAIZ / "datos" / "gold_standard_privado" / "gold_standard_v1.csv"
SALIDA_DEFECTO = RAIZ / "resultados" / "baseline_v1.json"
COLUMNA_TEXTO = "texto_normalizado"
COLUMNA_ETIQUETA = "etiqueta_final"
MODELO_SEMANTICO_DEFECTO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SEMILLA_DEFECTO = 42
TAM_PRUEBA_DEFECTO = 0.2
UMBRAL_REDUNDANCIA_DEFECTO = 0.30


def _fijar_semillas(semilla: int) -> None:
    """Fija las semillas de las fuentes de aleatoriedad no cubiertas por
    `random_state` explícito en sklearn (reproducibilidad, ver CLAUDE.md)."""
    random.seed(semilla)
    np.random.seed(semilla)


def _cargar_gold_standard(ruta: Path) -> pd.DataFrame:
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el gold standard en {ruta}. Es un archivo privado, no "
            "versionado (ver .gitignore): este experimento solo puede reproducirse "
            "en un entorno donde exista localmente, no se generan datos sintéticos "
            "para sustituirlo."
        )
    gold = pd.read_csv(ruta, encoding="utf-8-sig")
    gold[COLUMNA_TEXTO] = gold[COLUMNA_TEXTO].fillna("")
    return gold


def _tasa_redundancia(
    ruta_gold: Path, vectores_por_id: dict, umbral: float
) -> dict[str, dict]:
    """Tasa de redundancia (candidatos RF/RNF) de cada representación, en un umbral fijo."""
    candidatos = cargar_candidatos(ruta_gold)
    resultado = {}
    for metodo, vectores in vectores_por_id.items():
        tabla, _ = barrer_umbrales(vectores, [umbral])
        fila = tabla.iloc[0]
        resultado[metodo] = {
            "umbral": float(fila["umbral"]),
            "grupos": int(fila["grupos"]),
            "total_candidatos": len(candidatos),
            "tasa_redundancia": float(fila["tasa_redundancia"]),
        }
    return resultado


def ejecutar_baseline(
    ruta_gold: Path,
    modelo_semantico: str,
    semilla: int,
    tam_prueba: float,
    umbral_redundancia: float,
    backend: str = "torch",
    archivo_modelo: str | None = None,
) -> dict:
    """Corre el experimento completo y devuelve el dict listo para volcar a JSON."""
    _fijar_semillas(semilla)

    gold = _cargar_gold_standard(ruta_gold)
    textos = gold[COLUMNA_TEXTO].tolist()
    etiquetas = gold[COLUMNA_ETIQUETA].tolist()

    resultado_tfidf = tfidf_logreg.entrenar(textos, etiquetas, semilla=semilla, tam_prueba=tam_prueba)
    X_test_tfidf = resultado_tfidf["vectorizador"].transformar(resultado_tfidf["textos_test"])
    y_pred_tfidf = resultado_tfidf["clasificador"].predict(X_test_tfidf)
    metricas_tfidf = calcular_metricas(resultado_tfidf["y_test"], list(y_pred_tfidf))

    representador = RepresentadorSemantico(
        modelo_semantico, semilla=semilla, backend=backend, archivo_modelo=archivo_modelo
    )
    representador.cargar()
    resultado_semantico = semantico_logreg.entrenar(
        textos, etiquetas, representador, semilla=semilla, tam_prueba=tam_prueba
    )
    X_test_semantico = representador.transformar(resultado_semantico["textos_test"])
    y_pred_semantico = resultado_semantico["clasificador"].predict(X_test_semantico)
    metricas_semantico = calcular_metricas(resultado_semantico["y_test"], list(y_pred_semantico))

    assert resultado_tfidf["indices_test"] == resultado_semantico["indices_test"], (
        "el split de tfidf y semántico debe coincidir exactamente para que la "
        "comparación sea válida (ver docstring de nucleo.clasificacion.semantico_logreg)"
    )

    candidatos = cargar_candidatos(ruta_gold)
    textos_candidatos = candidatos[COLUMNA_TEXTO].tolist()
    vectores_por_metodo = {
        "tfidf": resultado_tfidf["vectorizador"].transformar(textos_candidatos),
        "semantico": representador.transformar(textos_candidatos),
    }
    redundancia = _tasa_redundancia(ruta_gold, vectores_por_metodo, umbral_redundancia)

    return {
        "fecha": datetime.now(timezone.utc).isoformat(),
        "dataset": ruta_gold.name,
        "n_total": len(gold),
        "semilla": semilla,
        "tam_prueba": tam_prueba,
        "n_train": len(resultado_tfidf["textos_train"]),
        "n_test": len(resultado_tfidf["textos_test"]),
        "modelo_semantico": modelo_semantico,
        "resultados": {
            "tfidf": {
                "precision_global": metricas_tfidf["precision_global"],
                "recall_global": metricas_tfidf["recall_global"],
                "f1_global": metricas_tfidf["f1_global"],
                "metricas_por_clase": metricas_tfidf["metricas_por_clase"],
                "matriz_confusion": metricas_tfidf["matriz_confusion"],
                "redundancia": redundancia["tfidf"],
            },
            "semantico": {
                "precision_global": metricas_semantico["precision_global"],
                "recall_global": metricas_semantico["recall_global"],
                "f1_global": metricas_semantico["f1_global"],
                "metricas_por_clase": metricas_semantico["metricas_por_clase"],
                "matriz_confusion": metricas_semantico["matriz_confusion"],
                "redundancia": redundancia["semantico"],
            },
        },
    }


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Experimento principal: semántico vs. TF-IDF sobre el gold standard."
    )
    parser.add_argument("--entrada", type=Path, default=GOLD_STANDARD_DEFECTO)
    parser.add_argument("--salida", type=Path, default=SALIDA_DEFECTO)
    parser.add_argument("--semilla", type=int, default=SEMILLA_DEFECTO)
    parser.add_argument("--tam-prueba", type=float, default=TAM_PRUEBA_DEFECTO)
    parser.add_argument("--modelo-semantico", default=MODELO_SEMANTICO_DEFECTO)
    parser.add_argument(
        "--backend", choices=["torch", "onnx"], default="torch",
        help="'onnx' permite usar --archivo-modelo con una variante cuantizada más liviana",
    )
    parser.add_argument("--archivo-modelo", default=None)
    parser.add_argument("--umbral-redundancia", type=float, default=UMBRAL_REDUNDANCIA_DEFECTO)
    args = parser.parse_args()

    resultado = ejecutar_baseline(
        ruta_gold=args.entrada,
        modelo_semantico=args.modelo_semantico,
        semilla=args.semilla,
        tam_prueba=args.tam_prueba,
        umbral_redundancia=args.umbral_redundancia,
        backend=args.backend,
        archivo_modelo=args.archivo_modelo,
    )

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open("w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"gold standard: {resultado['n_total']} filas (train={resultado['n_train']}, test={resultado['n_test']})")
    for metodo, datos in resultado["resultados"].items():
        print(
            f"{metodo:10s} precision={datos['precision_global']:.4f} "
            f"recall={datos['recall_global']:.4f} f1={datos['f1_global']:.4f} "
            f"redundancia={datos['redundancia']['tasa_redundancia']:.4f}"
        )
    print(f"\nresultados guardados en {args.salida}")


if __name__ == "__main__":
    _cli()
