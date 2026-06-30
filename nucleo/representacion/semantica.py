"""Representación semántica contextual mediante Sentence-Transformers."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class RepresentadorSemantico:
    """Genera embeddings densos usando un modelo Sentence-Transformers local."""

    def __init__(self, nombre_modelo: str, semilla: int = 42) -> None:
        self.nombre_modelo = nombre_modelo
        self.semilla = semilla
        self._modelo = None

    def cargar(self) -> None:
        """Carga el modelo desde disco (sin conexión tras la descarga inicial)."""
        from sentence_transformers import SentenceTransformer  # importación diferida

        self._modelo = SentenceTransformer(self.nombre_modelo)

    def transformar(self, textos: list[str]) -> NDArray[np.float32]:
        """Convierte una lista de textos en una matriz de embeddings."""
        if self._modelo is None:
            raise RuntimeError("Llama a cargar() antes de transformar().")
        return self._modelo.encode(textos, convert_to_numpy=True)
