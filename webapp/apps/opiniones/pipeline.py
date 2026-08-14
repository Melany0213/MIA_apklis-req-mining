"""Puente entre la subida manual de opiniones (web) y el pipeline del `nucleo/`.

No reimplementa preprocesamiento, representación ni clasificación: solo
carga una vez por proceso los mismos componentes que usa
`nucleo.scripts.exportar_propuestas` (fases 2-4) y valida/parsea el archivo
subido por el analista antes de pasarlo por ese pipeline ya existente.
"""

from __future__ import annotations

import io
from functools import lru_cache

import pandas as pd
from django.conf import settings

from nucleo.clasificacion.zero_shot import ClasificadorZeroShot
from nucleo.pipeline import Pipeline
from nucleo.preprocesamiento.lematizador import Lematizador
from nucleo.representacion.semantica import RepresentadorSemantico

EXTENSIONES_PERMITIDAS = {"csv", "json"}
COLUMNA_TEXTO = "texto"


class ArchivoOpinionesInvalido(ValueError):
    """Error de formato o contenido en el archivo subido, con mensaje para el usuario."""


class ComponentesPipeline:
    """Agrupa el lematizador y el clasificador ya cargados, listos para usar."""

    def __init__(self, lematizador: Lematizador, clasificador: ClasificadorZeroShot) -> None:
        self.lematizador = lematizador
        self.clasificador = clasificador


@lru_cache(maxsize=1)
def obtener_componentes() -> ComponentesPipeline:
    """Carga spaCy y el modelo semántico una sola vez por proceso (son costosos)."""
    lematizador = Lematizador(settings.MODELO_SPACY)
    lematizador.cargar()

    representador = RepresentadorSemantico(settings.MODELO_EMBEDDINGS, semilla=settings.SEMILLA_ALEATORIA)
    representador.cargar()
    clasificador = ClasificadorZeroShot(representador)

    return ComponentesPipeline(lematizador, clasificador)


@lru_cache(maxsize=1)
def obtener_pipeline() -> Pipeline:
    """Crea y prepara el orquestador de fases 2-4 (`nucleo.pipeline.Pipeline`)
    una sola vez por proceso, para `POST /api/clasificar/`. Usa la propuesta
    zero-shot (sin `ruta_modelo`), igual que `obtener_componentes` de este
    mismo módulo — no hay un clasificador entrenado configurado por defecto.
    """
    pipeline = Pipeline(
        modelo_spacy=settings.MODELO_SPACY,
        modelo_embeddings=settings.MODELO_EMBEDDINGS,
        semilla=settings.SEMILLA_ALEATORIA,
    )
    pipeline.preparar()
    return pipeline


def leer_corpus(archivo) -> pd.DataFrame:
    """Parsea el archivo subido (.csv o .json) a un DataFrame con columna `texto`.

    Lanza `ArchivoOpinionesInvalido` con un mensaje claro ante extensión no
    soportada, contenido vacío, encoding incorrecto, parseo fallido o
    ausencia de la columna/campo `texto`.
    """
    nombre = getattr(archivo, "name", "")
    extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    if extension not in EXTENSIONES_PERMITIDAS:
        raise ArchivoOpinionesInvalido("El archivo debe tener extensión .csv o .json.")

    contenido = archivo.read()
    if not contenido:
        raise ArchivoOpinionesInvalido("El archivo está vacío.")

    try:
        texto_decodificado = contenido.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ArchivoOpinionesInvalido(
            "No se pudo leer el archivo: el encoding debe ser UTF-8 (se acepta con o sin BOM)."
        ) from exc

    try:
        if extension == "csv":
            corpus = pd.read_csv(io.StringIO(texto_decodificado))
        else:
            corpus = pd.read_json(io.StringIO(texto_decodificado))
    except ValueError as exc:
        raise ArchivoOpinionesInvalido(f"El archivo {extension.upper()} está mal formado: {exc}") from exc

    if corpus.empty:
        raise ArchivoOpinionesInvalido("El archivo no contiene ninguna opinión.")

    if COLUMNA_TEXTO not in corpus.columns:
        raise ArchivoOpinionesInvalido(
            f"Falta la columna/campo obligatorio '{COLUMNA_TEXTO}'. "
            f"Columnas encontradas: {', '.join(corpus.columns) or '(ninguna)'}."
        )

    corpus[COLUMNA_TEXTO] = corpus[COLUMNA_TEXTO].astype(str).str.strip()
    corpus = corpus[corpus[COLUMNA_TEXTO].astype(bool)].reset_index(drop=True)
    if corpus.empty:
        raise ArchivoOpinionesInvalido(f"Ninguna fila tiene contenido en la columna '{COLUMNA_TEXTO}'.")

    return corpus
