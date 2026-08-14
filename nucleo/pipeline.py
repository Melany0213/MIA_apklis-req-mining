"""Orquesta las fases 2-4 del método sobre opiniones ya extraídas (fase 1).

Uso mínimo (propuesta zero-shot, sin clasificador entrenado):
    from nucleo.pipeline import Pipeline

    pipeline = Pipeline()
    pipeline.preparar()
    propuestas = pipeline.ejecutar(["La app cierra sola", "Buena app"])

Uso con un clasificador ya entrenado (ver nucleo/clasificacion/*_logreg.py):
    from pathlib import Path

    pipeline = Pipeline(metodo="tfidf", ruta_modelo=Path("datos/modelos/tfidf_logreg.joblib"))
    pipeline.preparar()
    propuestas = pipeline.ejecutar(["La app cierra sola"])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import joblib

from nucleo.clasificacion.zero_shot import ClasificadorZeroShot
from nucleo.preprocesamiento import preprocesar
from nucleo.preprocesamiento.lematizador import Lematizador
from nucleo.representacion.semantica import RepresentadorSemantico

Etiqueta = Literal["RF", "RNF", "Ruido"]
MetodoRepresentacion = Literal["semantico", "tfidf"]
MetodoPropuesta = Literal["zero_shot", "semantico", "tfidf"]

MODELO_SPACY_DEFECTO = "es_core_news_md"
MODELO_SEMANTICO_DEFECTO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@dataclass
class Propuesta:
    """Resultado de clasificar una opinión (pendiente de validación humana)."""

    texto_original: str
    etiqueta: Etiqueta
    confianza: float
    metodo: MetodoPropuesta
    texto_preprocesado: str = ""


def _crear_lematizador(modelo_spacy: str) -> Lematizador:
    """Crea y carga un lematizador de spaCy.

    Aislado en una función de módulo (en vez de instanciarlo directamente en
    `Pipeline.preparar`) para que las pruebas puedan sustituirlo por un doble
    con `monkeypatch.setattr` sin cargar spaCy de verdad.
    """
    lematizador = Lematizador(modelo_spacy)
    lematizador.cargar()
    return lematizador


def _crear_clasificador_zero_shot(modelo_embeddings: str, semilla: int) -> ClasificadorZeroShot:
    """Crea un clasificador zero-shot (sin entrenar) sobre embeddings recién cargados.

    Aislado igual que `_crear_lematizador`, para permitir un doble de prueba.
    """
    representador = RepresentadorSemantico(modelo_embeddings, semilla=semilla)
    representador.cargar()
    return ClasificadorZeroShot(representador)


def _cargar_modelo_entrenado(ruta_modelo: Path, metodo: MetodoRepresentacion) -> tuple[object, object]:
    """Carga desde un .joblib el representador/vectorizador ya ajustado y el
    clasificador entrenado, en el mismo formato que escriben
    `nucleo.clasificacion.tfidf_logreg._cli` y
    `nucleo.clasificacion.semantico_logreg._cli` (joblib.dump con las claves
    "vectorizador"/"representador" + "clasificador").
    """
    datos = joblib.load(ruta_modelo)
    clave_representador = "vectorizador" if metodo == "tfidf" else "representador"
    return datos[clave_representador], datos["clasificador"]


@dataclass
class Pipeline:
    """Coordinador de las fases 2 (preprocesamiento), 3 (representación) y 4
    (clasificación) del método, sobre una lista de opiniones ya extraídas
    (fase 1, fuera de este orquestador).

    Sin `ruta_modelo`, solo `metodo="semantico"` está disponible: cae a una
    propuesta zero-shot (`nucleo.clasificacion.zero_shot`), sin entrenar.
    `metodo="tfidf"` exige un clasificador ya entrenado (`ruta_modelo`)
    porque TF-IDF necesita un vocabulario ajustado de antemano — no existe
    (ni se inventa aquí) un equivalente zero-shot para TF-IDF.
    """

    metodo: MetodoRepresentacion = "semantico"
    semilla: int = 42
    modelo_spacy: str = MODELO_SPACY_DEFECTO
    modelo_embeddings: str = MODELO_SEMANTICO_DEFECTO
    ruta_modelo: Path | None = None

    _lematizador: Lematizador | None = field(default=None, init=False, repr=False)
    _representador: object = field(default=None, init=False, repr=False)
    _clasificador: object = field(default=None, init=False, repr=False)
    _metodo_propuesta: MetodoPropuesta | None = field(default=None, init=False, repr=False)

    def preparar(self) -> None:
        """Carga el lematizador y el clasificador (llamar una vez antes de ejecutar())."""
        self._lematizador = _crear_lematizador(self.modelo_spacy)

        if self.ruta_modelo is not None:
            self._representador, self._clasificador = _cargar_modelo_entrenado(
                self.ruta_modelo, self.metodo
            )
            self._metodo_propuesta = self.metodo
        elif self.metodo == "semantico":
            self._representador = None
            self._clasificador = _crear_clasificador_zero_shot(self.modelo_embeddings, self.semilla)
            self._metodo_propuesta = "zero_shot"
        else:
            raise ValueError(
                "metodo='tfidf' requiere un clasificador ya entrenado: pasa `ruta_modelo` "
                "apuntando a un .joblib de nucleo.clasificacion.tfidf_logreg (TF-IDF no admite "
                "propuesta zero-shot porque su vocabulario debe ajustarse de antemano)."
            )

    def ejecutar(self, opiniones: list[str]) -> list[Propuesta]:
        """Preprocesa, representa y clasifica una lista de opiniones crudas."""
        if self._lematizador is None or self._clasificador is None:
            raise RuntimeError("Llama a preparar() antes de ejecutar().")

        textos_preprocesados = [preprocesar(texto, self._lematizador) for texto in opiniones]

        if isinstance(self._clasificador, ClasificadorZeroShot):
            etiquetas_confianzas = self._clasificador.proponer(textos_preprocesados)
        else:
            X = self._representador.transformar(textos_preprocesados)
            etiquetas = self._clasificador.predict(X)
            confianzas = self._clasificador.predict_proba(X).max(axis=1)
            etiquetas_confianzas = list(zip(etiquetas, confianzas))

        return [
            Propuesta(
                texto_original=texto_original,
                etiqueta=etiqueta,
                confianza=float(confianza),
                metodo=self._metodo_propuesta,
                texto_preprocesado=texto_preprocesado,
            )
            for texto_original, texto_preprocesado, (etiqueta, confianza) in zip(
                opiniones, textos_preprocesados, etiquetas_confianzas
            )
        ]
