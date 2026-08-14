"""Mide la redundancia del catálogo de requisitos candidatos (fase 3, comparación
semántico vs. TF-IDF).

Toma del gold standard (`datos/gold_standard_privado/gold_standard_v1.csv`) las
opiniones ya validadas como `RF` o `RNF` — los requisitos candidatos reales, sin
Ruido — y, para las dos representaciones ya implementadas en el proyecto
(`nucleo.representacion.tfidf.RepresentadorTFIDF` y
`nucleo.representacion.semantica.RepresentadorSemantico`), agrupa por similitud
de coseno con `AgglomerativeClustering` (`linkage='average'`, sin número fijo de
grupos) barriendo el umbral de distancia. La tasa de redundancia de un umbral es
`1 - (grupos / total_candidatos)`: cuantos más candidatos caen en el mismo
grupo, más alta la redundancia detectada.

No modifica el pipeline ni reentrena nada: reutiliza el vectorizador TF-IDF ya
ajustado en `datos/modelos/tfidf_logreg.joblib` (fase 4,
`nucleo.clasificacion.tfidf_logreg`) y el mismo modelo Sentence-Transformers
preentrenado que usa el resto del proyecto.

Uso:
    python -m nucleo.evaluacion.redundancia \
        --entrada datos/gold_standard_privado/gold_standard_v1.csv \
        --tfidf-modelo datos/modelos/tfidf_logreg.joblib

    # con agrupamiento manual de referencia (columnas id_opinion, id_grupo):
    python -m nucleo.evaluacion.redundancia --agrupamiento-manual datos/gold_standard_privado/grupos_manuales.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import (
    adjusted_rand_score,
    completeness_score,
    homogeneity_score,
)
from sklearn.metrics.pairwise import cosine_similarity

from nucleo.representacion.semantica import RepresentadorSemantico

COLUMNA_TEXTO = "texto_normalizado"
COLUMNA_ETIQUETA = "etiqueta_final"
ETIQUETAS_CANDIDATAS = ["RF", "RNF"]

MODELO_SEMANTICO_DEFECTO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TFIDF_MODELO_DEFECTO = Path("datos/modelos/tfidf_logreg.joblib")

UMBRAL_MIN_DEFECTO = 0.10
UMBRAL_MAX_DEFECTO = 0.60
UMBRAL_PASO_DEFECTO = 0.05

# Elegido tras inspeccionar el barrido sobre el gold standard v1 (ver
# docs/bitacora-experimentos.md): a partir de 0.30 la tasa semántica deja de
# crecer a saltos grandes entre pasos consecutivos y los grupos que forma en
# la inspección manual (fichero de grupos exportado) siguen siendo
# parafraseos genuinos de la misma solicitud, no candidatos distintos fundidos
# por error. Es el punto de equilibrio entre no sobre-fusionar candidatos
# distintos y sí capturar reformulaciones del mismo requisito.
UMBRAL_OPERATIVO_DEFECTO = 0.30


def cargar_candidatos(ruta_gold: Path) -> pd.DataFrame:
    """Carga el gold standard y filtra los requisitos candidatos (RF o RNF).

    `id_opinion` es la posición de la fila en el CSV original del gold
    standard (no hay un identificador propio en el archivo); sirve para poder
    cruzar contra un agrupamiento manual de referencia por fila.
    """
    gold = pd.read_csv(ruta_gold, encoding="utf-8-sig")
    gold[COLUMNA_TEXTO] = gold[COLUMNA_TEXTO].fillna("")
    candidatos = gold[gold[COLUMNA_ETIQUETA].isin(ETIQUETAS_CANDIDATAS)].copy()
    candidatos = candidatos.reset_index(drop=False).rename(columns={"index": "id_opinion"})
    return candidatos.reset_index(drop=True)


def cargar_vectorizador_tfidf(ruta_modelo: Path) -> Any:
    """Carga el vectorizador TF-IDF ya ajustado por `nucleo.clasificacion.tfidf_logreg`."""
    modelo = joblib.load(ruta_modelo)
    return modelo["vectorizador"]


def cargar_representador_semantico(
    nombre_modelo: str, backend: str, archivo_modelo: str | None
) -> RepresentadorSemantico:
    """Carga el mismo modelo Sentence-Transformers preentrenado que usa el resto del proyecto."""
    representador = RepresentadorSemantico(nombre_modelo, backend=backend, archivo_modelo=archivo_modelo)
    representador.cargar()
    return representador


def matriz_similitud_coseno(vectores: np.ndarray) -> np.ndarray:
    """Matriz de similitud de coseno entre todos los pares de candidatos."""
    return cosine_similarity(vectores)


def barrer_umbrales(
    vectores: np.ndarray, umbrales: list[float]
) -> tuple[pd.DataFrame, dict[float, np.ndarray]]:
    """Agrupa con AgglomerativeClustering (coseno, enlace promedio) en cada umbral.

    Devuelve la tabla de grupos/tasa de redundancia por umbral y, aparte, las
    etiquetas de grupo asignadas a cada candidato en cada umbral (para poder
    exportar los grupos o compararlos contra un agrupamiento manual sin
    recalcular el clustering).
    """
    total = vectores.shape[0]
    filas = []
    etiquetas_por_umbral: dict[float, np.ndarray] = {}
    for umbral in umbrales:
        modelo = AgglomerativeClustering(
            metric="cosine",
            linkage="average",
            distance_threshold=umbral,
            n_clusters=None,
        )
        etiquetas = modelo.fit_predict(vectores)
        grupos = int(modelo.n_clusters_)
        tasa = 1 - grupos / total
        filas.append({"umbral": round(umbral, 2), "grupos": grupos, "tasa_redundancia": round(tasa, 4)})
        etiquetas_por_umbral[round(umbral, 2)] = etiquetas
    return pd.DataFrame(filas), etiquetas_por_umbral


def construir_tabla_comparativa(tabla_tfidf: pd.DataFrame, tabla_semantico: pd.DataFrame) -> pd.DataFrame:
    """Combina los barridos de TF-IDF y semántico en una sola tabla, por umbral."""
    combinada = tabla_tfidf.merge(tabla_semantico, on="umbral", suffixes=("_tfidf", "_semantico"))
    return combinada.rename(
        columns={
            "grupos_tfidf": "grupos_tfidf",
            "tasa_redundancia_tfidf": "tasa_tfidf",
            "grupos_semantico": "grupos_semantico",
            "tasa_redundancia_semantico": "tasa_semantico",
        }
    )


def exportar_grupos(
    candidatos: pd.DataFrame, etiquetas_grupo: np.ndarray, ruta_salida: Path
) -> None:
    """Escribe, en texto plano, cada grupo semántico con sus opiniones (inspección manual)."""
    grupos: dict[int, list[tuple[int, str]]] = {}
    for id_opinion, texto, etiqueta in zip(
        candidatos["id_opinion"], candidatos["texto_original"], etiquetas_grupo
    ):
        grupos.setdefault(int(etiqueta), []).append((int(id_opinion), texto))

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        for grupo_id in sorted(grupos, key=lambda g: -len(grupos[g])):
            miembros = grupos[grupo_id]
            f.write(f"=== Grupo {grupo_id} ({len(miembros)} opiniones) ===\n")
            for id_opinion, texto in miembros:
                f.write(f"  [{id_opinion}] {texto}\n")
            f.write("\n")


def evaluar_contra_manual(
    candidatos: pd.DataFrame, etiquetas_auto: np.ndarray, ruta_manual: Path
) -> dict[str, float | int]:
    """Compara un agrupamiento automático contra un agrupamiento manual de referencia.

    `ruta_manual` es un CSV con columnas `id_opinion, id_grupo`. Solo se
    comparan los `id_opinion` presentes en ambos lados (join interno) — si el
    agrupamiento manual no cubre el 100% de los candidatos, el ARI/homogeneidad/
    completitud se calculan igual sobre el subconjunto cubierto.
    """
    manual = pd.read_csv(ruta_manual)
    automatico = pd.DataFrame(
        {"id_opinion": candidatos["id_opinion"].to_numpy(), "id_grupo_auto": etiquetas_auto}
    )
    combinado = automatico.merge(manual, on="id_opinion", how="inner")
    if combinado.empty:
        raise ValueError(
            f"Ningún id_opinion de {ruta_manual} coincide con los candidatos del gold standard."
        )

    y_manual = combinado["id_grupo"]
    y_auto = combinado["id_grupo_auto"]
    return {
        "ari": round(float(adjusted_rand_score(y_manual, y_auto)), 4),
        "homogeneidad": round(float(homogeneity_score(y_manual, y_auto)), 4),
        "completitud": round(float(completeness_score(y_manual, y_auto)), 4),
        "n_comparadas": len(combinado),
    }


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Mide la redundancia del catálogo de requisitos candidatos (RF/RNF del gold "
            "standard) comparando TF-IDF contra embeddings semánticos."
        )
    )
    parser.add_argument(
        "--entrada",
        type=Path,
        default=Path("datos/gold_standard_privado/gold_standard_v1.csv"),
        help="CSV del gold standard",
    )
    parser.add_argument("--tfidf-modelo", type=Path, default=TFIDF_MODELO_DEFECTO)
    parser.add_argument("--modelo-semantico", default=MODELO_SEMANTICO_DEFECTO)
    parser.add_argument(
        "--backend",
        choices=["torch", "onnx"],
        default="torch",
        help="'onnx' permite usar --archivo-modelo con una variante cuantizada más liviana",
    )
    parser.add_argument("--archivo-modelo", default=None)
    parser.add_argument("--umbral-min", type=float, default=UMBRAL_MIN_DEFECTO)
    parser.add_argument("--umbral-max", type=float, default=UMBRAL_MAX_DEFECTO)
    parser.add_argument("--umbral-paso", type=float, default=UMBRAL_PASO_DEFECTO)
    parser.add_argument(
        "--umbral-operativo",
        type=float,
        default=UMBRAL_OPERATIVO_DEFECTO,
        help="umbral al que se exportan los grupos semánticos y se calculan los índices contra el agrupamiento manual",
    )
    parser.add_argument(
        "--agrupamiento-manual",
        type=Path,
        default=None,
        help="CSV opcional (columnas id_opinion, id_grupo) con un agrupamiento manual de referencia",
    )
    parser.add_argument(
        "--salida-tabla",
        type=Path,
        default=Path("datos/gold_standard_privado/redundancia_umbrales.csv"),
    )
    parser.add_argument(
        "--salida-grupos",
        type=Path,
        default=Path("datos/gold_standard_privado/redundancia_grupos_semantico.txt"),
    )
    args = parser.parse_args()

    candidatos = cargar_candidatos(args.entrada)
    total = len(candidatos)
    print(f"requisitos candidatos (RF + RNF): {total}")
    print(candidatos[COLUMNA_ETIQUETA].value_counts().to_string())

    textos = candidatos[COLUMNA_TEXTO].tolist()

    vectorizador_tfidf = cargar_vectorizador_tfidf(args.tfidf_modelo)
    X_tfidf = vectorizador_tfidf.transformar(textos)

    representador_semantico = cargar_representador_semantico(
        args.modelo_semantico, args.backend, args.archivo_modelo
    )
    X_semantico = representador_semantico.transformar(textos)

    # a) matriz de similitud de coseno (diagnóstico: similitud media entre pares)
    sim_tfidf = matriz_similitud_coseno(X_tfidf)
    sim_semantico = matriz_similitud_coseno(X_semantico)
    triu = np.triu_indices(total, k=1)
    print(f"similitud de coseno media entre pares — TF-IDF: {sim_tfidf[triu].mean():.4f}, "
          f"semántico: {sim_semantico[triu].mean():.4f}")

    # b) + c) barrido de umbral de distancia y tasa de redundancia
    umbrales = [
        round(u, 2)
        for u in np.arange(args.umbral_min, args.umbral_max + args.umbral_paso / 2, args.umbral_paso)
    ]
    tabla_tfidf, etiquetas_tfidf = barrer_umbrales(X_tfidf, umbrales)
    tabla_semantico, etiquetas_semantico = barrer_umbrales(X_semantico, umbrales)

    tabla_comparativa = construir_tabla_comparativa(tabla_tfidf, tabla_semantico)
    print()
    print(tabla_comparativa.to_string(index=False))

    args.salida_tabla.parent.mkdir(parents=True, exist_ok=True)
    tabla_comparativa.to_csv(args.salida_tabla, index=False, encoding="utf-8")
    print(f"\ntabla comparativa guardada en {args.salida_tabla}")

    # umbral operativo: grupos semánticos exportados para inspección manual
    umbral_operativo = round(args.umbral_operativo, 2)
    if umbral_operativo not in etiquetas_semantico:
        raise ValueError(
            f"--umbral-operativo={umbral_operativo} no está en el barrido {umbrales}; "
            "usa un valor dentro de --umbral-min/--umbral-max/--umbral-paso."
        )
    exportar_grupos(candidatos, etiquetas_semantico[umbral_operativo], args.salida_grupos)
    fila_operativa = tabla_comparativa[tabla_comparativa["umbral"] == umbral_operativo].iloc[0]
    print(
        f"\numbral operativo = {umbral_operativo} -> "
        f"grupos TF-IDF={int(fila_operativa['grupos_tfidf'])} (tasa={fila_operativa['tasa_tfidf']}), "
        f"grupos semántico={int(fila_operativa['grupos_semantico'])} (tasa={fila_operativa['tasa_semantico']})"
    )
    print(f"grupos semánticos exportados en {args.salida_grupos}")

    if args.agrupamiento_manual is not None:
        print(f"\ncomparación contra agrupamiento manual ({args.agrupamiento_manual}) en umbral={umbral_operativo}:")
        resultado_tfidf = evaluar_contra_manual(
            candidatos, etiquetas_tfidf[umbral_operativo], args.agrupamiento_manual
        )
        resultado_semantico = evaluar_contra_manual(
            candidatos, etiquetas_semantico[umbral_operativo], args.agrupamiento_manual
        )
        print(f"  TF-IDF:     {resultado_tfidf}")
        print(f"  semántico:  {resultado_semantico}")


if __name__ == "__main__":
    _cli()
