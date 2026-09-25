"""Pruebas de las comprobaciones previas a exponer ECO por un túnel.

Cada caso de aquí corresponde a un fallo real que, sin esta comprobación, se
manifiesta en caliente como una página que no carga o una validación que se
rechaza sin decir por qué — y con alguien mirando al otro lado del enlace.
"""

from __future__ import annotations

import pytest

from scripts.servir_local import revisar_configuracion

CONFIG_TUNEL_CORRECTA = {
    "debug": False,
    "hosts_permitidos": ["localhost", "127.0.0.1", ".devtunnels.ms"],
    "origenes_csrf": ["https://*.devtunnels.ms"],
    "detras_de_proxy": True,
    "tunel": "vscode",
}


def test_configuracion_correcta_no_reporta_nada():
    assert revisar_configuracion(**CONFIG_TUNEL_CORRECTA) == []


def test_sin_tunel_no_exige_nada_de_tunel():
    """Servir solo en local no necesita dominios ni proxy."""
    problemas = revisar_configuracion(
        debug=True,
        hosts_permitidos=["localhost"],
        origenes_csrf=[],
        detras_de_proxy=False,
        tunel=None,
    )

    assert problemas == []


def test_debug_activo_con_tunel_es_un_problema():
    """Exponer a internet con DEBUG deja ver el código y la configuración."""
    problemas = revisar_configuracion(**{**CONFIG_TUNEL_CORRECTA, "debug": True})

    assert len(problemas) == 1
    assert "DEBUG" in problemas[0]


def test_falta_el_dominio_en_allowed_hosts():
    problemas = revisar_configuracion(
        **{**CONFIG_TUNEL_CORRECTA, "hosts_permitidos": ["localhost"]}
    )

    assert any("DisallowedHost" in p for p in problemas)


def test_falta_el_origen_csrf():
    """El fallo más traicionero: la aplicación se ve, pero no se puede validar."""
    problemas = revisar_configuracion(**{**CONFIG_TUNEL_CORRECTA, "origenes_csrf": []})

    assert any("CSRF" in p for p in problemas)


def test_falta_marcar_que_hay_un_proxy_delante():
    problemas = revisar_configuracion(
        **{**CONFIG_TUNEL_CORRECTA, "detras_de_proxy": False}
    )

    assert any("DETRAS_DE_PROXY" in p for p in problemas)


@pytest.mark.parametrize(
    ("tunel", "dominio"),
    [("vscode", ".devtunnels.ms"), ("cloudflare", ".trycloudflare.com")],
)
def test_cada_tunel_exige_su_propio_dominio(tunel, dominio):
    problemas = revisar_configuracion(
        debug=False,
        hosts_permitidos=["localhost", dominio],
        origenes_csrf=[f"https://*{dominio}"],
        detras_de_proxy=True,
        tunel=tunel,
    )

    assert problemas == []
