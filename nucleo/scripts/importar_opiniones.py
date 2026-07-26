"""Importa opiniones crudas + su propuesta de clasificación (fase 4) a la webapp.

Une dos artefactos de `nucleo/` que hoy solo viven en CSV con la base de
datos de la webapp, para poder recorrer la fase 5 (validación humana) desde
el navegador en vez de editar un CSV a mano. Las filas se importan siempre
con `estado="propuesto"`: aunque el CSV de origen ya tenga una
`etiqueta_final` de una validación previa (p. ej. el gold standard), esta
importación no la reutiliza — sería hacer pasar por "validación humana en la
webapp" algo que en realidad se validó en el CSV. La cola en pantalla es una
demostración en vivo del mecanismo de la fase 5, no una re-carga del gold
standard congelado.

Uso:
    python -m nucleo.scripts.importar_opiniones \
        --corpus datos/corpus_crudo/cu.uci.android.apklis.csv \
        --propuestas datos/corpus_crudo/cu.uci.android.apklis_propuestas.csv \
        --limite 100
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
CORPUS_DEFECTO = RAIZ / "datos" / "corpus_crudo" / "cu.uci.android.apklis.csv"
PROPUESTAS_DEFECTO = RAIZ / "datos" / "corpus_crudo" / "cu.uci.android.apklis_propuestas.csv"


def _preparar_django() -> None:
    sys.path.insert(0, str(RAIZ))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapp.config.settings")
    import django

    django.setup()


def importar_a_bd(corpus: pd.DataFrame, propuestas: pd.DataFrame) -> tuple[int, int]:
    """Crea `Opinion` y `Requisito` (estado="propuesto") a partir de corpus + propuestas.

    Comparte esta lógica el importador por consola y la subida manual desde
    la webapp: ambos alimentan la misma cola de validación humana (fase 5).
    Devuelve (opiniones_creadas, requisitos_creados).
    """
    from webapp.apps.opiniones.models import Opinion
    from webapp.apps.validacion.models import Requisito

    creadas_opinion = 0
    creadas_requisito = 0
    for (_, fila_corpus), (_, fila_prop) in zip(corpus.iterrows(), propuestas.iterrows()):
        fecha_publicacion = pd.to_datetime(fila_corpus.get("fecha_publicacion"), errors="coerce")
        opinion, creada = Opinion.objects.get_or_create(
            texto_original=fila_corpus["texto"],
            autor_anon=fila_corpus.get("id_autor_anonimo", ""),
            defaults={
                "texto_normalizado": fila_prop.get("texto_normalizado", ""),
                "fecha_publicacion": None if pd.isna(fecha_publicacion) else fecha_publicacion,
                "calificacion": fila_corpus.get("calificacion"),
                "aplicacion": fila_corpus.get("aplicacion", ""),
                "fuente": fila_corpus.get("fuente", ""),
            },
        )
        if creada:
            creadas_opinion += 1

        _, creado_req = Requisito.objects.get_or_create(
            opinion=opinion,
            defaults={
                "etiqueta_propuesta": fila_prop["etiqueta_propuesta"],
                "confianza": fila_prop.get("confianza"),
                "metodo": "zero_shot",
                "estado": "propuesto",
            },
        )
        if creado_req:
            creadas_requisito += 1

    return creadas_opinion, creadas_requisito


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Importa opiniones + propuestas (zero-shot) a las tablas Opinion/Requisito."
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS_DEFECTO)
    parser.add_argument("--propuestas", type=Path, default=PROPUESTAS_DEFECTO)
    parser.add_argument("--limite", type=int, default=None, help="importar solo las primeras N filas")
    args = parser.parse_args()

    _preparar_django()

    corpus = pd.read_csv(args.corpus)
    propuestas = pd.read_csv(args.propuestas, encoding="utf-8-sig")
    if len(corpus) != len(propuestas):
        raise SystemExit(
            f"corpus ({len(corpus)} filas) y propuestas ({len(propuestas)} filas) no coinciden; "
            "deben venir del mismo `exportar_propuestas` para poder alinearse por índice."
        )

    if args.limite:
        corpus = corpus.head(args.limite)
        propuestas = propuestas.head(args.limite)

    creadas_opinion, creadas_requisito = importar_a_bd(corpus, propuestas)

    print(f"opiniones creadas: {creadas_opinion} (de {len(corpus)} filas procesadas)")
    print(f"requisitos (propuestas) creados: {creadas_requisito}")


if __name__ == "__main__":
    _cli()
