"""Resolución de la conexión a PostgreSQL a partir de una sola URL.

Los entornos gestionados (Neon, Render, Railway…) entregan la base de datos
como una única variable `DATABASE_URL` en vez de las cinco variables `DB_*`
que usa el entorno local. Este módulo traduce la primera al diccionario que
espera `DATABASES` de Django, para no tener dos formas distintas de
configurar lo mismo repartidas por `settings.py`.

El entorno local sigue funcionando exactamente igual que antes: si no hay
`DATABASE_URL`, `settings.py` cae a las variables `DB_*` de siempre.
"""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

ESQUEMAS_VALIDOS = ("postgres", "postgresql")
HOSTS_LOCALES = ("localhost", "127.0.0.1", "::1", "")


class URLBaseDatosInvalida(ValueError):
    """La `DATABASE_URL` no se pudo interpretar; el mensaje explica qué falta."""


def desde_url(url: str) -> dict:
    """Convierte una URL `postgresql://usuario:clave@host:puerto/base` en la
    configuración de `DATABASES["default"]`.

    El TLS no se deja al azar: si la URL no trae `sslmode` y el host no es
    local, se exige `require`. Un despliegue contra una base gestionada que
    viaje en claro sería una fuga de datos, y aquí las opiniones son datos de
    personas reales (anonimizadas, pero datos al fin).
    """
    partes = urlparse(url)

    if partes.scheme not in ESQUEMAS_VALIDOS:
        raise URLBaseDatosInvalida(
            f"Esquema no soportado: '{partes.scheme or '(vacío)'}'. "
            f"Se espera una URL {' o '.join(ESQUEMAS_VALIDOS)}://"
        )
    if not partes.hostname:
        raise URLBaseDatosInvalida("La URL no indica el host de la base de datos.")

    nombre = unquote(partes.path).lstrip("/")
    if not nombre:
        raise URLBaseDatosInvalida("La URL no indica el nombre de la base de datos.")

    consulta = parse_qs(partes.query)
    sslmode = consulta.get("sslmode", [None])[0]
    if sslmode is None:
        sslmode = "disable" if partes.hostname in HOSTS_LOCALES else "require"

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": nombre,
        "USER": unquote(partes.username or ""),
        "PASSWORD": unquote(partes.password or ""),
        "HOST": partes.hostname,
        "PORT": str(partes.port or 5432),
        "OPTIONS": {"sslmode": sslmode},
    }
