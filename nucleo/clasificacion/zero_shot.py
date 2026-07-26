"""Propuesta de etiqueta por similitud semántica (zero-shot), sin entrenar.

No es el clasificador final de la fase 4: sirve para *proponer* una etiqueta
inicial sobre una muestra del corpus, a partir de la similitud coseno contra
frases prototipo de cada clase, usando el mismo `RepresentadorSemantico` de
la fase 3. La propuesta es solo un punto de partida — la etiqueta final la
decide un humano en la fase 5 (ver `nucleo/evaluacion/muestra_validacion.py`).
Evita la circularidad de entrenar un clasificador con etiquetas que todavía
no existen.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from nucleo.representacion.semantica import RepresentadorSemantico

PROTOTIPOS: dict[str, list[str]] = {
    "RF": [
        "el usuario pide que la aplicación tenga una función nueva que no existe",
        "sugerencia para añadir una opción, un botón o una funcionalidad concreta",
        "el usuario reporta que una función específica no funciona y debería funcionar",
    ],
    "RNF": [
        "el usuario se queja del rendimiento, la velocidad o la estabilidad de la aplicación",
        "la aplicación se cierra sola, se congela, tarda en cargar o consume muchos datos o batería",
        "queja sobre la usabilidad, el diseño, la seguridad o la accesibilidad de la aplicación",
    ],
    "Ruido": [
        "opinión que solo alaba o critica la aplicación en general sin información útil",
        "comentario genérico de agradecimiento, insulto o saludo sin relación con una mejora concreta",
        "publicidad, spam o contenido sin relación con la aplicación",
    ],
}


def _normalizar(matriz: NDArray[np.float32]) -> NDArray[np.float32]:
    normas = np.linalg.norm(matriz, axis=1, keepdims=True)
    normas[normas == 0] = 1.0
    return matriz / normas


class ClasificadorZeroShot:
    """Propone RF/RNF/Ruido por similitud coseno a frases prototipo por clase."""

    def __init__(
        self,
        representador: RepresentadorSemantico,
        prototipos: dict[str, list[str]] = PROTOTIPOS,
    ) -> None:
        self._representador = representador
        self._etiquetas = list(prototipos.keys())
        self._prototipos_norm = {
            etiqueta: _normalizar(representador.transformar(frases))
            for etiqueta, frases in prototipos.items()
        }

    def proponer(self, textos: list[str]) -> list[tuple[str, float]]:
        """Para cada texto, devuelve (etiqueta_propuesta, confianza).

        La confianza es un softmax sobre la similitud máxima de cada texto
        contra las frases prototipo de cada clase: no es una probabilidad
        calibrada, solo indica cuán marcada fue la clase ganadora frente a
        las otras dos.
        """
        embeddings = _normalizar(self._representador.transformar(textos))
        similitudes_por_clase = np.stack(
            [
                (embeddings @ self._prototipos_norm[etiqueta].T).max(axis=1)
                for etiqueta in self._etiquetas
            ],
            axis=1,
        )
        exponenciales = np.exp(similitudes_por_clase - similitudes_por_clase.max(axis=1, keepdims=True))
        pesos = exponenciales / exponenciales.sum(axis=1, keepdims=True)
        indices = similitudes_por_clase.argmax(axis=1)
        return [
            (self._etiquetas[indice], float(pesos[fila, indice]))
            for fila, indice in enumerate(indices)
        ]
