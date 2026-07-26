"""Pruebas del muestreo estratificado y de la generación de propuestas (fase 5, previo)."""

from __future__ import annotations

import pandas as pd

from nucleo.evaluacion.muestra_validacion import generar_propuestas, muestrear_estratificado


def _corpus_de_prueba() -> pd.DataFrame:
    filas = []
    for calificacion, cantidad in [(1, 40), (2, 20), (3, 10), (4, 10), (5, 20)]:
        for i in range(cantidad):
            filas.append(
                {
                    "texto": f"opinion {calificacion}-{i}",
                    "calificacion": calificacion,
                    "aplicacion": "cu.uci.android.apklis",
                }
            )
    return pd.DataFrame(filas)


def test_muestrear_estratificado_respeta_proporciones_por_calificacion() -> None:
    corpus = _corpus_de_prueba()  # 100 filas

    muestra = muestrear_estratificado(corpus, n=20, semilla=42)

    conteo = muestra["calificacion"].value_counts().to_dict()
    assert len(muestra) == 20
    assert conteo[1] == 8  # 40% del corpus -> 40% de la muestra
    assert conteo[5] == 4  # 20% del corpus -> 20% de la muestra


def test_muestrear_estratificado_es_reproducible_con_la_misma_semilla() -> None:
    corpus = _corpus_de_prueba()

    muestra_a = muestrear_estratificado(corpus, n=20, semilla=7)
    muestra_b = muestrear_estratificado(corpus, n=20, semilla=7)

    assert sorted(muestra_a["texto"]) == sorted(muestra_b["texto"])


class _ClasificadorFalso:
    """Doble de prueba: propone siempre la misma etiqueta con confianza fija."""

    def proponer(self, textos: list[str]) -> list[tuple[str, float]]:
        return [("RF", 0.5) for _ in textos]


def test_generar_propuestas_agrega_columnas_para_validar() -> None:
    muestra = pd.DataFrame(
        {
            "texto": ["falta modo oscuro", "  se cierra sola   solaaaa"],
            "calificacion": [3, 1],
            "aplicacion": ["cu.uci.android.apklis"] * 2,
        }
    )

    resultado = generar_propuestas(muestra, _ClasificadorFalso())

    assert list(resultado["etiqueta_propuesta"]) == ["RF", "RF"]
    assert (resultado["etiqueta_validada"] == "").all()
    assert (resultado["notas_validador"] == "").all()
    assert resultado.loc[1, "texto_limpio"] == "se cierra sola solaa"
