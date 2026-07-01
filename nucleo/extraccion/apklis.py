"""Cliente HTTP para la API pública de Apklis (fase 1 — extracción).

Apklis expone en https://api.apklis.cu/ la misma API REST que consume su
sitio web (https://www.apklis.cu), sin autenticación para lectura de
catálogo y reseñas públicas. Este cliente es deliberadamente conservador:
espera entre peticiones y se identifica con un User-Agent descriptivo para
no sobrecargar la plataforma.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import requests

URL_BASE = "https://api.apklis.cu/"
AGENTE_USUARIO_DEFECTO = (
    "MIA-tesis-UCI/0.1 "
    "(investigacion academica - identificacion de requisitos desde opiniones; "
    "extraccion respetuosa con espera entre peticiones)"
)


class ClienteApklis:
    """Cliente paginado y respetuoso hacia la API pública de Apklis."""

    def __init__(
        self,
        sesion: requests.Session | None = None,
        espera_entre_peticiones: float = 1.0,
        tiempo_limite: float = 15.0,
        agente_usuario: str = AGENTE_USUARIO_DEFECTO,
    ) -> None:
        self._sesion = sesion or requests.Session()
        self._sesion.headers.setdefault("User-Agent", agente_usuario)
        self._sesion.headers.setdefault("Accept", "application/json")
        self._espera = espera_entre_peticiones
        self._tiempo_limite = tiempo_limite

    def _paginar(self, ruta: str, params: dict[str, Any]) -> Iterator[dict]:
        """Recorre un endpoint paginado de DRF (limit/offset) siguiendo `next`."""
        url: str | None = URL_BASE + ruta
        parametros_actuales: dict[str, Any] | None = params
        while url:
            respuesta = self._sesion.get(url, params=parametros_actuales, timeout=self._tiempo_limite)
            respuesta.raise_for_status()
            datos = respuesta.json()
            yield from datos.get("results", [])
            url = datos.get("next")
            # `next` ya trae los parámetros codificados; no hay que repetirlos.
            parametros_actuales = None
            if url:
                time.sleep(self._espera)

    def listar_aplicaciones(self, **filtros: Any) -> Iterator[dict]:
        """Recorre el catálogo público de aplicaciones."""
        yield from self._paginar("v2/application/", filtros)

    def listar_opiniones(
        self, package_name: str, solo_publicas: bool = True, tam_pagina: int = 100
    ) -> Iterator[dict]:
        """Recorre las reseñas de una aplicación, identificada por su package_name.

        `tam_pagina` controla cuántas reseñas se piden por petición HTTP
        (menos peticiones totales = más respetuoso con la plataforma).
        """
        params: dict[str, Any] = {"application": package_name, "limit": tam_pagina}
        if solo_publicas:
            params["public"] = "true"
        yield from self._paginar("v2/review/", params)
