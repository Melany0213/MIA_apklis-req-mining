"""Configuración común de las pruebas.

Aísla la suite del almacenamiento de estáticos con manifiesto que usa el
despliegue: sin esto, `pytest` solo pasaría después de haber corrido
`collectstatic`, y cualquiera que clone el repositorio (o la CI en un runner
limpio) vería fallar pruebas que no tienen nada que ver con lo que prueban.
El manifiesto es cosa del despliegue —el `Dockerfile` sí lo genera—, no de las
pruebas.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def estaticos_sin_manifiesto(settings) -> None:
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
