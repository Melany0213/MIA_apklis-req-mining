"""Limpieza y normalización de texto crudo (fase 2, previo a la lematización).

Adaptado al español informal de Cuba: enlaces, menciones y repeticiones de
caracteres típicas de la escritura coloquial ("buenisimaaaa", "jajajaja").
No elimina emojis: aportan señal de opinión (satisfacción/queja) que la
representación semántica puede aprovechar.
"""

from __future__ import annotations

import re

_URL = re.compile(r"https?://\S+|www\.\S+")
_MENCION = re.compile(r"@\w+")
_REPETICION_CARACTER = re.compile(r"(.)\1{2,}")
_REPETICION_SILABA = re.compile(r"(..)\1{2,}")
_ESPACIOS = re.compile(r"\s+")


def limpiar_texto(texto: str) -> str:
    """Normaliza una opinión cruda antes de lematizarla."""
    texto = _URL.sub(" ", texto)
    texto = _MENCION.sub(" ", texto)
    texto = _REPETICION_CARACTER.sub(r"\1\1", texto)
    texto = _REPETICION_SILABA.sub(r"\1\1", texto)
    texto = _ESPACIOS.sub(" ", texto).strip()
    return texto
