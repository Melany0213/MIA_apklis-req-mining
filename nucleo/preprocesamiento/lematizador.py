"""Lematización con spaCy (fase 2), sobre texto ya limpiado."""

from __future__ import annotations

import spacy
from spacy.language import Language

MODELO_DEFECTO = "es_core_news_sm"


class Lematizador:
    """Envoltorio sobre un pipeline de spaCy para lematizar opiniones ya limpias."""

    def __init__(self, nombre_modelo: str = MODELO_DEFECTO) -> None:
        self.nombre_modelo = nombre_modelo
        self._nlp: Language | None = None

    def cargar(self) -> None:
        """Carga el modelo de spaCy (descargado localmente, sin conexión tras la instalación)."""
        self._nlp = spacy.load(self.nombre_modelo, disable=["ner", "parser"])

    def lematizar(self, texto_limpio: str) -> str:
        """Devuelve los lemas en minúscula del texto, sin espacios ni puntuación."""
        if self._nlp is None:
            raise RuntimeError("Llama a cargar() antes de lematizar().")
        doc = self._nlp(texto_limpio)
        lemas = [t.lemma_.lower() for t in doc if not t.is_space and not t.is_punct]
        return " ".join(lemas)
