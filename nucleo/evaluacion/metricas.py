"""Cálculo de métricas de evaluación del clasificador (sin dependencias de Django)."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix

ETIQUETAS: list[str] = ["RF", "RNF", "Ruido"]


def calcular_metricas(
    y_true: list[str],
    y_pred: list[str],
    etiquetas: list[str] = ETIQUETAS,
) -> dict:
    """Calcula precisión, recall, F1 global y por clase, más matriz de confusión.

    Retorna un dict listo para guardar en CorridaEvaluacion.
    """
    report = classification_report(
        y_true, y_pred,
        labels=etiquetas,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_true, y_pred, labels=etiquetas).tolist()

    metricas_por_clase = {
        etiqueta: {
            "precision": round(report[etiqueta]["precision"], 4),
            "recall": round(report[etiqueta]["recall"], 4),
            "f1": round(report[etiqueta]["f1-score"], 4),
            "soporte": int(report[etiqueta]["support"]),
        }
        for etiqueta in etiquetas
        if etiqueta in report
    }

    return {
        "precision_global": round(report["weighted avg"]["precision"], 4),
        "recall_global": round(report["weighted avg"]["recall"], 4),
        "f1_global": round(report["weighted avg"]["f1-score"], 4),
        "metricas_por_clase": metricas_por_clase,
        "matriz_confusion": cm,
    }


def comparar_corridas(corridas: list[dict]) -> dict:
    """Dado un listado de dicts con métricas, devuelve índice y valor del mejor F1."""
    if not corridas:
        return {}
    mejor_idx = int(np.argmax([c["f1_global"] for c in corridas]))
    return {"mejor_idx": mejor_idx, "mejor_f1": corridas[mejor_idx]["f1_global"]}
