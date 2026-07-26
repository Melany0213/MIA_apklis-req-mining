"""Diccionario de Normalización de Jerga Local (DNJL) — fase 2, previo a la
representación vectorial.

Aplica las 4 categorías de reglas de la Tabla 7 (jerga tecnológica cubana,
abreviaturas informales, errores fonético-ortográficos frecuentes y variantes
verbales) mediante mapeo directo mediante expresiones regulares con límite de
palabra. Se ejecuta después de `limpiar_texto` y antes de la lematización con
spaCy y de la representación vectorial (semántica o TF-IDF), tal como describe
el documento de la tesis. Es un módulo propio, no forma parte silenciosa de la
lematización: cubre jerga y errores que un lematizador estándar no corrige.
"""

from __future__ import annotations

import re

NEOLOGISMOS_TECNOLOGICOS = {
    "pincha": "funciona",
    "funde": "agota",
    "lag": "retraso",
    "crashea": "falla",
}

ABREVIATURAS_INFORMALES = {
    "xq": "porque",
    "q": "que",
    "d": "de",
    "x": "por",
}

ERRORES_FONETICOS_ORTOGRAFICOS = {
    "aser": "hacer",
    "habrir": "abrir",
    "bota": "vota",
    "movil": "móvil",
}

LEMATIZACION_VERBOS = {
    "actualizando": "actualizar",
    "actualicé": "actualizar",
    "actualiza": "actualizar",
}

REGLAS_DNJL: dict[str, dict[str, str]] = {
    "neologismos_tecnologicos": NEOLOGISMOS_TECNOLOGICOS,
    "abreviaturas_informales": ABREVIATURAS_INFORMALES,
    "errores_foneticos_ortograficos": ERRORES_FONETICOS_ORTOGRAFICOS,
    "lematizacion_verbos": LEMATIZACION_VERBOS,
}


def _compilar_patron(diccionario: dict[str, str]) -> re.Pattern[str]:
    terminos = sorted(diccionario, key=len, reverse=True)
    alternativas = "|".join(re.escape(termino) for termino in terminos)
    return re.compile(rf"\b({alternativas})\b", re.IGNORECASE)


_DICCIONARIO_PLANO: dict[str, str] = {}
for _reglas in REGLAS_DNJL.values():
    _DICCIONARIO_PLANO.update(_reglas)
_PATRON_TERMINOS = _compilar_patron(_DICCIONARIO_PLANO)


def normalizar_dnjl(texto: str) -> str:
    """Sustituye jerga local, abreviaturas y errores frecuentes por su forma
    normalizada (Tabla 7), respetando límites de palabra y sin distinguir
    mayúsculas/minúsculas en la búsqueda."""

    def _reemplazar(coincidencia: re.Match[str]) -> str:
        return _DICCIONARIO_PLANO[coincidencia.group(0).lower()]

    return _PATRON_TERMINOS.sub(_reemplazar, texto)
