"""Sirve ECO desde esta máquina para enseñarlo por un túnel público.

Es el despliegue provisional mientras no haya servidor propio: la aplicación
corre aquí y un túnel (VS Code o Cloudflare) le da una URL de internet
temporal. Ver `docs/DESPLIEGUE.md`, sección "Despliegue temporal desde tu PC".

No usa el `runserver` de Django, que es de desarrollo y atiende de uno en
uno: usa **waitress**, un servidor WSGI de verdad que además funciona en
Windows (gunicorn, el del contenedor, no).

Uso:
    python scripts/servir_local.py                  # solo en esta máquina
    python scripts/servir_local.py --tunel vscode   # preparado para el túnel de VS Code
    python scripts/servir_local.py --tunel cloudflare

El argumento `--tunel` no abre el túnel (eso es un programa aparte): sirve
para comprobar antes de arrancar que la configuración admitirá ese dominio,
porque el fallo típico —Django respondiendo "DisallowedHost" o rechazando la
validación por CSRF— no dice en ningún sitio que le falta un dominio.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Dominios de los túneles soportados. Django acepta el punto inicial como
# comodín de subdominio, que es justo lo que hace falta: el túnel asigna un
# subdominio distinto en cada sesión.
DOMINIOS_TUNEL = {
    "vscode": ".devtunnels.ms",
    "cloudflare": ".trycloudflare.com",
}


def revisar_configuracion(
    *,
    debug: bool,
    hosts_permitidos: list[str],
    origenes_csrf: list[str],
    detras_de_proxy: bool,
    tunel: str | None,
) -> list[str]:
    """Devuelve la lista de problemas de configuración, vacía si todo está bien.

    Separada del arranque para poder probarla: son exactamente los errores
    que, en caliente, se manifiestan como páginas en blanco o rechazos sin
    explicación.
    """
    problemas: list[str] = []

    if tunel is not None and debug:
        problemas.append(
            "DJANGO_DEBUG está en True y vas a exponer la aplicación a internet. "
            "Con DEBUG activo, cualquier error muestra tu código y tu configuración "
            "al visitante. Ponlo en False en el archivo .env."
        )

    if tunel is None:
        return problemas

    dominio = DOMINIOS_TUNEL[tunel]

    if dominio not in hosts_permitidos:
        problemas.append(
            f"Falta '{dominio}' en DJANGO_ALLOWED_HOSTS; sin eso Django responde "
            f"'DisallowedHost' a todo el que abra el enlace."
        )

    origen_esperado = f"https://*{dominio}"
    if origen_esperado not in origenes_csrf:
        problemas.append(
            f"Falta '{origen_esperado}' en DJANGO_CSRF_TRUSTED_ORIGINS; sin eso se "
            f"puede mirar la aplicación pero no validar ni descartar (falla el CSRF)."
        )

    if not detras_de_proxy:
        problemas.append(
            "Falta DJANGO_DETRAS_DE_PROXY=True; el túnel termina el HTTPS por su "
            "cuenta y Django necesita saberlo para las cookies seguras."
        )

    return problemas


def _preparar_django() -> None:
    sys.path.insert(0, str(RAIZ))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapp.config.settings")
    import django

    django.setup()


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Sirve ECO en esta máquina con waitress.")
    parser.add_argument("--puerto", type=int, default=8000)
    parser.add_argument(
        "--tunel",
        choices=sorted(DOMINIOS_TUNEL),
        default=None,
        help="comprueba que la configuración admite el dominio de ese túnel",
    )
    parser.add_argument(
        "--saltar-preparacion",
        action="store_true",
        help="no aplicar migraciones ni recolectar estáticos (arranque más rápido)",
    )
    args = parser.parse_args()

    _preparar_django()

    from django.conf import settings
    from django.core.management import call_command

    problemas = revisar_configuracion(
        debug=settings.DEBUG,
        hosts_permitidos=list(settings.ALLOWED_HOSTS),
        origenes_csrf=list(settings.CSRF_TRUSTED_ORIGINS),
        detras_de_proxy=bool(getattr(settings, "SECURE_PROXY_SSL_HEADER", None)),
        tunel=args.tunel,
    )
    if problemas:
        print("No se puede arrancar; falta configuración en tu archivo .env:\n")
        for problema in problemas:
            print(f"  - {problema}\n")
        print("En .env.example tienes las líneas listas para copiar.")
        raise SystemExit(1)

    if not args.saltar_preparacion:
        print("==> Migraciones")
        call_command("migrate", interactive=False, verbosity=0)
        print("==> Estáticos")
        call_command("collectstatic", interactive=False, verbosity=0)

    from waitress import serve

    from webapp.config.wsgi import application

    # Solo 127.0.0.1: el túnel se conecta desde esta misma máquina, así que no
    # hace falta exponer la aplicación al resto de la red local.
    print(f"\n==> ECO escuchando en http://127.0.0.1:{args.puerto}")
    if args.tunel == "vscode":
        print("    Ahora: pestaña PORTS -> Forward a Port -> "
              f"{args.puerto} -> clic derecho -> Port Visibility -> Public")
    elif args.tunel == "cloudflare":
        print(f"    Ahora, en otra terminal: cloudflared tunnel --url http://localhost:{args.puerto}")
    print("    Para parar: Ctrl+C\n")

    serve(application, host="127.0.0.1", port=args.puerto, threads=6)


if __name__ == "__main__":
    _cli()
