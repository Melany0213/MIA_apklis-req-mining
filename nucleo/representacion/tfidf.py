"""Representación TF-IDF — línea base de comparación."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from sklearn.feature_extraction.text import TfidfVectorizer


class RepresentadorTFIDF:
    """Vectorizador TF-IDF configurable para el corpus en español."""

    def __init__(self, max_features: int = 5000) -> None:
        self._vectorizador = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )

    def ajustar_transformar(self, textos: list[str]) -> NDArray[np.float32]:
        """Ajusta el vocabulario y devuelve la matriz TF-IDF (entrenamiento)."""
        return self._vectorizador.fit_transform(textos).toarray().astype(np.float32)

    def transformar(self, textos: list[str]) -> NDArray[np.float32]:
        """Aplica el vocabulario ya ajustado (inferencia)."""
        return self._vectorizador.transform(textos).toarray().astype(np.float32)
