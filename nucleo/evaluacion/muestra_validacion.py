"""Genera la muestra que un humano debe validar antes de aceptar cualquier
etiqueta (fase 5).

Toma un corpus crudo ya extraído (fase 1), aplica limpieza y DNJL (fase 2) y una
propuesta zero-shot por similitud semántica (ver `nucleo.clasificacion.zero_shot`)
sobre una muestra estratificada por calificación. El resultado es un CSV con
columnas vacías `etiqueta_validada` y `notas_validador`: nadie debe tratar
`etiqueta_propuesta` como resultado final, es solo el punto de partida que el
especialista corrige o confirma.

Uso:
    python -m nucleo.evaluacion.muestra_validacion \
        --entrada datos/corpus_crudo/cu.uci.android.apklis.csv \
        --n 500
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from nucleo.clasificacion.zero_shot import ClasificadorZeroShot
from nucleo.preprocesamiento.dnjl import normalizar_dnjl
from nucleo.preprocesamiento.limpieza import limpiar_texto
from nucleo.representacion.semantica import RepresentadorSemantico

MODELO_SEMANTICO_DEFECTO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLUMNAS_SALIDA = [
    "texto_original",
    "texto_limpio",
    "calificacion",
    "aplicacion",
    "etiqueta_propuesta",
    "confianza_propuesta",
    "etiqueta_validada",
    "notas_validador",
]


def muestrear_estratificado(
    corpus: pd.DataFrame,
    n: int,
    columna_estrato: str = "calificacion",
    semilla: int = 42,
) -> pd.DataFrame:
    """Toma una muestra de tamaño ~n, proporcional a cada valor de `columna_estrato`.

    Reparte n proporcionalmente al tamaño de cada estrato (p. ej. cada
    calificación de 1 a 5) para que la muestra refleje la composición real
    del corpus en vez de sobrerrepresentar una calificación.
    """
    proporcion = n / len(corpus)
    partes = [
        grupo.sample(frac=proporcion, random_state=semilla)
        for _, grupo in corpus.groupby(columna_estrato)
    ]
    muestra = pd.concat(partes)
    if len(muestra) > n:
        muestra = muestra.sample(n=n, random_state=semilla)
    return muestra.reset_index(drop=True)


def generar_propuestas(muestra: pd.DataFrame, clasificador: ClasificadorZeroShot) -> pd.DataFrame:
    """Añade texto_limpio, etiqueta_propuesta y confianza_propuesta a la muestra."""
    muestra = muestra.copy()
    muestra["texto_limpio"] = muestra["texto"].map(limpiar_texto).map(normalizar_dnjl)
    propuestas = clasificador.proponer(muestra["texto_limpio"].tolist())
    muestra["etiqueta_propuesta"] = [etiqueta for etiqueta, _ in propuestas]
    muestra["confianza_propuesta"] = [round(confianza, 4) for _, confianza in propuestas]
    muestra["etiqueta_validada"] = ""
    muestra["notas_validador"] = ""
    muestra = muestra.rename(columns={"texto": "texto_original"})
    return muestra[COLUMNAS_SALIDA]


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Genera la muestra a validar por un humano (fase 5), con propuesta zero-shot."
    )
    parser.add_argument("--entrada", type=Path, required=True, help="CSV del corpus crudo (fase 1)")
    parser.add_argument("--salida", type=Path, default=None, help="ruta del CSV de validación")
    parser.add_argument("--n", type=int, default=500, help="tamaño de la muestra a validar")
    parser.add_argument("--semilla", type=int, default=42)
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

    corpus = pd.read_csv(args.entrada)
    muestra = muestrear_estratificado(corpus, n=args.n, semilla=args.semilla)

    representador = RepresentadorSemantico(
        args.modelo_semantico,
        semilla=args.semilla,
        backend=args.backend,
        archivo_modelo=args.archivo_modelo,
    )
    representador.cargar()
    clasificador = ClasificadorZeroShot(representador)

    resultado = generar_propuestas(muestra, clasificador)

    salida = args.salida or args.entrada.with_name(args.entrada.stem + "_muestra_validacion.csv")
    resultado.to_csv(salida, index=False, encoding="utf-8")
    print(f"{len(resultado)} opiniones listas para validar en {salida}")


if __name__ == "__main__":
    _cli()
