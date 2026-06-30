"""Orquesta las fases 1–4 del método sobre un corpus de opiniones.

Uso mínimo:
    from nucleo.pipeline import Pipeline
    pipeline = Pipeline()
    propuestas = pipeline.ejecutar(opiniones=["La app cierra sola", "Buena app"])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Etiqueta = Literal["RF", "RNF", "Ruido"]


@dataclass
class Propuesta:
    """Resultado de clasificar una opinión (pendiente de validación humana)."""

    texto_original: str
    etiqueta: Etiqueta
    confianza: float
    metodo: Literal["semantico", "tfidf"]
    texto_preprocesado: str = ""


@dataclass
class Pipeline:
    """Coordinador de las cuatro primeras fases del método."""

    metodo: Literal["semantico", "tfidf"] = "semantico"
    semilla: int = 42
    _listo: bool = field(default=False, init=False, repr=False)

    def preparar(self) -> None:
        """Carga modelos y prepara el pipeline (llamar una vez antes de ejecutar)."""
        # TODO: instanciar y cargar preprocesador, representador y clasificador
        self._listo = True

    def ejecutar(self, opiniones: list[str]) -> list[Propuesta]:
        """Clasifica una lista de opiniones y devuelve propuestas sin validar."""
        if not self._listo:
            raise RuntimeError("Llama a preparar() antes de ejecutar().")
        # TODO: conectar fases reales
        raise NotImplementedError("Pipeline aún en construcción.")
