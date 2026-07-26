"""Representación semántica contextual mediante Sentence-Transformers."""

from __future__ import annotations

import os
from typing import Literal

import numpy as np
from numpy.typing import NDArray


class RepresentadorSemantico:
    """Genera embeddings densos usando un modelo Sentence-Transformers local.

    Por defecto usa el backend `torch` en precisión completa (la configuración
    reproducible de referencia para la tesis). `backend="onnx"` + `archivo_modelo`
    permite cargar una variante cuantizada del mismo modelo (mismos pesos
    entrenados, menor precisión numérica) — útil solo cuando la descarga del
    modelo completo no es viable por ancho de banda; debe documentarse en la
    bitácora de experimentos si se usa para una corrida reportada.
    """

    def __init__(
        self,
        nombre_modelo: str,
        semilla: int = 42,
        backend: Literal["torch", "onnx"] = "torch",
        archivo_modelo: str | None = None,
    ) -> None:
        self.nombre_modelo = nombre_modelo
        self.semilla = semilla
        self.backend = backend
        self.archivo_modelo = archivo_modelo
        self._modelo = None

    def cargar(self) -> None:
        """Carga el modelo desde disco (sin conexión tras la descarga inicial).

        Fuerza el modo sin conexión de `huggingface_hub`: si no se hace, la
        librería intenta contactar al Hub para comprobar actualizaciones
        incluso con el modelo ya cacheado localmente, y en un entorno sin
        salida a internet la carga se cuelga en vez de fallar rápido.
        """
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

        from sentence_transformers import SentenceTransformer  # importación diferida

        model_kwargs = {"file_name": self.archivo_modelo} if self.archivo_modelo else {}
        self._modelo = SentenceTransformer(
            self.nombre_modelo, backend=self.backend, model_kwargs=model_kwargs
        )

    def transformar(self, textos: list[str]) -> NDArray[np.float32]:
        """Convierte una lista de textos en una matriz de embeddings."""
        if self._modelo is None:
            raise RuntimeError("Llama a cargar() antes de transformar().")
        return self._modelo.encode(textos, convert_to_numpy=True)
