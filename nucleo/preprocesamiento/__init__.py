"""Fase 2 — Preprocesamiento lingüístico (spaCy, español informal cubano)."""

from __future__ import annotations

from nucleo.preprocesamiento.dnjl import REGLAS_DNJL, normalizar_dnjl
from nucleo.preprocesamiento.lematizador import Lematizador
from nucleo.preprocesamiento.limpieza import limpiar_texto


def preprocesar(texto: str, lematizador: Lematizador) -> str:
    """Aplica limpieza, DNJL y lematización a una opinión cruda."""
    texto_normalizado = normalizar_dnjl(limpiar_texto(texto))
    return lematizador.lematizar(texto_normalizado)


__all__ = ["Lematizador", "REGLAS_DNJL", "limpiar_texto", "normalizar_dnjl", "preprocesar"]
