"""Construcción del corpus crudo de opiniones a partir de Apklis (fase 1).

Descarga reseñas públicas vía ClienteApklis, las anonimiza inmediatamente
y produce un CSV en datos/corpus_crudo/ (carpeta no versionada). No depende
de Django: puede ejecutarse como script independiente.

Uso:
    python -m nucleo.extraccion.corpus --paquete cu.todus.android --limite 300
"""

from __future__ import annotations

import argparse
import csv
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import islice
from pathlib import Path

from nucleo.extraccion.anonimizacion import anonimizar_autor
from nucleo.extraccion.apklis import ClienteApklis

CAMPOS_CSV = [
    "id_autor_anonimo", "texto", "calificacion", "fecha_publicacion",
    "aplicacion", "version_app", "fuente",
]


@dataclass
class OpinionCruda:
    """Una opinión anonimizada tal como sale de la fase 1, sin preprocesar."""

    id_autor_anonimo: str
    texto: str
    calificacion: float
    fecha_publicacion: datetime
    aplicacion: str
    version_app: str
    fuente: str = "apklis"


def _a_opinion_cruda(reseña: dict) -> OpinionCruda | None:
    """Traduce una reseña cruda de la API a OpinionCruda, o None si no aporta."""
    texto = (reseña.get("comment") or "").strip()
    if not texto:
        return None
    identificador = (reseña.get("user") or {}).get("username") or ""
    return OpinionCruda(
        id_autor_anonimo=anonimizar_autor(identificador) if identificador else "anonimo",
        texto=texto,
        calificacion=float(reseña.get("rating") or 0),
        fecha_publicacion=datetime.fromisoformat(reseña["published"]),
        aplicacion=reseña.get("application", ""),
        version_app=reseña.get("version") or "",
    )


def construir_corpus(
    cliente: ClienteApklis,
    package_name: str,
    limite: int | None = None,
) -> list[OpinionCruda]:
    """Descarga y anonimiza las opiniones públicas de una app de Apklis."""
    crudas: Iterable[dict] = cliente.listar_opiniones(package_name)
    if limite is not None:
        crudas = islice(crudas, limite)
    return [op for r in crudas if (op := _a_opinion_cruda(r)) is not None]


def guardar_csv(opiniones: list[OpinionCruda], ruta: Path) -> None:
    """Guarda el corpus anonimizado en CSV."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS_CSV)
        escritor.writeheader()
        for opinion in opiniones:
            fila = asdict(opinion)
            fila["fecha_publicacion"] = opinion.fecha_publicacion.isoformat()
            escritor.writerow(fila)


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Extrae y anonimiza opiniones de una app de Apklis.")
    parser.add_argument("--paquete", required=True, help="package_name en Apklis, p.ej. cu.todus.android")
    parser.add_argument("--limite", type=int, default=None, help="máximo de opiniones a descargar")
    parser.add_argument("--salida", type=Path, default=None, help="ruta del CSV de salida")
    parser.add_argument("--espera", type=float, default=1.0, help="segundos de espera entre peticiones")
    args = parser.parse_args()

    cliente = ClienteApklis(espera_entre_peticiones=args.espera)
    opiniones = construir_corpus(cliente, args.paquete, limite=args.limite)

    salida = args.salida or Path("datos/corpus_crudo") / f"{args.paquete}.csv"
    guardar_csv(opiniones, salida)
    print(f"{len(opiniones)} opiniones guardadas en {salida}")


if __name__ == "__main__":
    _cli()
