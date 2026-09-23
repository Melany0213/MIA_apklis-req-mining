"""Exporta una propuesta de etiqueta (RF/RNF/Ruido) por opinión, a partir del
preprocesamiento completo y el clasificador zero-shot ya existentes.

No es la fase 5 ni sustituye al módulo de validación (`nucleo.evaluacion.
muestra_validacion`, que muestrea y deja columnas para validar en el propio
CSV). Este script procesa el corpus completo que se le indique y produce un
CSV plano pensado para revisión manual externa (p. ej. en Excel): la
propuesta del clasificador nunca se trata como resultado final.

Pipeline aplicado a cada opinión: limpieza → DNJL → lematización spaCy
(`nucleo.preprocesamiento.preprocesar`) → embedding semántico → similitud a
prototipos (`nucleo.clasificacion.zero_shot.ClasificadorZeroShot`).

Uso:
    python -m nucleo.scripts.exportar_propuestas \
        --entrada datos/corpus_crudo/cu.uci.android.apklis.csv \
        --salida datos/corpus_crudo/cu.uci.android.apklis_propuestas.csv

Junto al CSV de salida se escribe siempre un `.metadata.json` con la
procedencia completa de la corrida (comando, modelo de spaCy y semántico
efectivos, semilla, commit de git, huella del DNJL vigente). Existe porque
el `texto_normalizado` del gold standard v1 (2026-07-04) se generó con este
mismo script sin que quedara registro de cómo — ver
`docs/ARQUITECTURA_ACTUAL.md` §7 y la bitácora, entrada 2026-08-19 ("Cierre
del punto 1 de la Fase 0"). No debe volver a perderse esa procedencia.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import spacy

from nucleo.clasificacion.zero_shot import ClasificadorZeroShot
from nucleo.preprocesamiento import REGLAS_DNJL, preprocesar
from nucleo.preprocesamiento.lematizador import Lematizador
from nucleo.representacion.semantica import RepresentadorSemantico

MODELO_SEMANTICO_DEFECTO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLUMNAS_SALIDA = ["texto_original", "texto_normalizado", "etiqueta_propuesta", "confianza"]
TAM_LOTE_PROGRESO_DEFECTO = 50


def _preprocesar_con_progreso(
    textos: list[str], lematizador: Lematizador, tam_lote: int
) -> list[str]:
    normalizados = []
    total = len(textos)
    for indice, texto in enumerate(textos, start=1):
        normalizados.append(preprocesar(texto, lematizador))
        if indice % tam_lote == 0 or indice == total:
            print(f"preprocesamiento: {indice}/{total}")
    return normalizados


def _clasificar_con_progreso(
    textos_normalizados: list[str], clasificador: ClasificadorZeroShot, tam_lote: int
) -> list[tuple[str, float]]:
    propuestas: list[tuple[str, float]] = []
    total = len(textos_normalizados)
    for inicio in range(0, total, tam_lote):
        lote = textos_normalizados[inicio : inicio + tam_lote]
        propuestas.extend(clasificador.proponer(lote))
        print(f"clasificación: {min(inicio + tam_lote, total)}/{total}")
    return propuestas


def generar_propuestas(
    corpus: pd.DataFrame,
    lematizador: Lematizador,
    clasificador: ClasificadorZeroShot,
    tam_lote_progreso: int = TAM_LOTE_PROGRESO_DEFECTO,
) -> pd.DataFrame:
    """Aplica el preprocesamiento completo y la propuesta zero-shot a cada opinión.

    Imprime avance cada `tam_lote_progreso` opiniones (preprocesamiento y
    clasificación por separado) para poder distinguir un proceso lento de
    uno colgado en corpus grandes.
    """
    resultado = pd.DataFrame({"texto_original": corpus["texto"]})
    resultado["texto_normalizado"] = _preprocesar_con_progreso(
        resultado["texto_original"].tolist(), lematizador, tam_lote_progreso
    )

    propuestas = _clasificar_con_progreso(
        resultado["texto_normalizado"].tolist(), clasificador, tam_lote_progreso
    )
    resultado["etiqueta_propuesta"] = [etiqueta for etiqueta, _ in propuestas]
    resultado["confianza"] = [round(confianza, 4) for _, confianza in propuestas]

    return resultado[COLUMNAS_SALIDA]


def _commit_git_actual() -> str | None:
    """Hash del commit actual del repo, o `None` si no aplica (sin git, sin
    repo, o árbol de trabajo sin commits). Aislada para poder sustituirla en
    pruebas sin depender de que el entorno de test tenga git disponible."""
    try:
        resultado = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return resultado.stdout.strip() if resultado.returncode == 0 else None


def _huella_dnjl() -> str:
    """Huella corta y determinista del diccionario DNJL vigente (no hay un
    número de versión propio del DNJL — esto cumple el mismo papel: detectar
    si cambió entre una corrida y otra)."""
    contenido = json.dumps(REGLAS_DNJL, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()[:12]


def construir_metadatos(
    *,
    argv: list[str],
    entrada: Path,
    n_filas_entrada: int,
    n_filas_salida: int,
    lematizador: Lematizador,
    representador: RepresentadorSemantico,
    semilla: int,
    commit_git: str | None,
) -> dict:
    """Arma el diccionario de procedencia que acompaña al CSV exportado.

    Separada de `_cli()` (que sí hace I/O: git, reloj) para poder probarla
    con valores fijos y deterministas.
    """
    return {
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "comando": shlex.join(argv),
        "commit_git": commit_git,
        "entrada": str(entrada),
        "n_filas_entrada": n_filas_entrada,
        "n_filas_salida": n_filas_salida,
        "modelo_spacy": lematizador.nombre_modelo,
        "version_spacy": spacy.__version__,
        "modelo_semantico": representador.nombre_modelo,
        "backend_semantico": representador.backend,
        "archivo_modelo_semantico": representador.archivo_modelo,
        "semilla": semilla,
        "huella_dnjl": _huella_dnjl(),
    }


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Exporta texto_original, texto_normalizado, etiqueta_propuesta y confianza a CSV."
    )
    parser.add_argument("--entrada", type=Path, required=True, help="CSV del corpus crudo (fase 1)")
    parser.add_argument("--salida", type=Path, default=None, help="ruta del CSV de salida")
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--modelo-semantico", default=MODELO_SEMANTICO_DEFECTO)
    parser.add_argument(
        "--modelo-spacy", default=None, help="nombre del modelo de spaCy (por defecto, el de Lematizador)"
    )
    parser.add_argument(
        "--backend",
        choices=["torch", "onnx"],
        default="torch",
        help="'onnx' permite usar --archivo-modelo con una variante cuantizada más liviana",
    )
    parser.add_argument(
        "--archivo-modelo",
        default=None,
        help="ruta del archivo .onnx dentro del repo (solo con --backend onnx)",
    )
    args = parser.parse_args()

    corpus = pd.read_csv(args.entrada)
    print(f"corpus leído: {len(corpus)} opiniones")

    print("cargando lematizador (spaCy)...")
    lematizador = Lematizador(args.modelo_spacy) if args.modelo_spacy else Lematizador()
    lematizador.cargar()

    print(f"cargando modelo semántico ({args.modelo_semantico}, backend={args.backend})...")
    representador = RepresentadorSemantico(
        args.modelo_semantico,
        semilla=args.semilla,
        backend=args.backend,
        archivo_modelo=args.archivo_modelo,
    )
    representador.cargar()
    clasificador = ClasificadorZeroShot(representador)

    resultado = generar_propuestas(corpus, lematizador, clasificador)

    salida = args.salida or args.entrada.with_name(args.entrada.stem + "_propuestas.csv")
    resultado.to_csv(salida, index=False, encoding="utf-8-sig")
    print(f"{len(resultado)} opiniones exportadas en {salida}")

    metadatos = construir_metadatos(
        argv=sys.argv,
        entrada=args.entrada,
        n_filas_entrada=len(corpus),
        n_filas_salida=len(resultado),
        lematizador=lematizador,
        representador=representador,
        semilla=args.semilla,
        commit_git=_commit_git_actual(),
    )
    ruta_metadatos = salida.with_suffix(".metadata.json")
    ruta_metadatos.write_text(json.dumps(metadatos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"metadatos de procedencia escritos en {ruta_metadatos}")


if __name__ == "__main__":
    _cli()
