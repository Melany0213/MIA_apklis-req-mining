"""Anonimización de identidades de autores de opiniones (obligatoria en fase 1)."""

from __future__ import annotations

import hashlib
import hmac
import os

_SAL_POR_DEFECTO = "mia-tesis-uci-sal-no-reversible"


def anonimizar_autor(identificador: str, sal: str | None = None) -> str:
    """Convierte un identificador de autor (username) en un hash no reversible.

    El mismo `identificador` produce siempre el mismo hash, lo que permite
    distinguir autores sin conservar su identidad. Ningún username, nombre
    real ni avatar debe guardarse más allá de esta función.

    La sal se toma de la variable de entorno MIA_SAL_ANONIMIZACION si existe;
    si no, se usa una sal fija de desarrollo (no reversible en la práctica,
    pero para producción se recomienda fijar la variable de entorno).
    """
    sal_efectiva = sal or os.environ.get("MIA_SAL_ANONIMIZACION", _SAL_POR_DEFECTO)
    return hmac.new(
        sal_efectiva.encode("utf-8"),
        identificador.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]
