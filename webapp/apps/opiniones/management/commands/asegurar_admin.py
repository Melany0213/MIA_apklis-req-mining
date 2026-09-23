"""Crea (o actualiza) el usuario administrador a partir del entorno.

En un despliegue gestionado no hay consola interactiva para
`createsuperuser`, y sin usuario nadie puede validar: la fase 5 quedaría
inaccesible. Las credenciales llegan por variables de entorno
(`DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD`), nunca escritas
en el código.

Es idempotente: si el usuario ya existe, solo se asegura de que siga siendo
superusuario, y únicamente le cambia la contraseña si se pide explícitamente
con `--actualizar-clave` (así un reinicio del contenedor no pisa una
contraseña que el administrador haya cambiado desde la interfaz).
"""

from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Asegura que exista el superusuario definido en las variables de entorno."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--actualizar-clave", action="store_true")

    def handle(self, *args, **opciones) -> None:
        usuario_nombre = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        clave = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

        if not usuario_nombre or not clave:
            self.stdout.write(
                "Sin DJANGO_SUPERUSER_USERNAME/PASSWORD en el entorno; no se crea ningún usuario."
            )
            return

        Usuario = get_user_model()
        usuario, creado = Usuario.objects.get_or_create(
            username=usuario_nombre,
            defaults={"email": os.environ.get("DJANGO_SUPERUSER_EMAIL", "")},
        )

        if creado or opciones["actualizar_clave"]:
            usuario.set_password(clave)

        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.save()

        accion = "creado" if creado else "verificado"
        self.stdout.write(self.style.SUCCESS(f"Usuario administrador '{usuario_nombre}' {accion}."))
