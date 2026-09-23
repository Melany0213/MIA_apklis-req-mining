"""Siembra el corpus de ejemplo en una base recién creada (despliegue).

Existe para que un despliegue limpio no arranque con la cola de validación
vacía. No es un atajo del método: las opiniones pasan por el **mismo**
pipeline de fases 2-4 que la subida manual del navegador y quedan en
`estado="propuesto"`, esperando a un humano. Nada entra como validado.

Es idempotente: si ya hay opiniones en la base, no hace nada (así puede
llamarse en cada arranque del contenedor sin duplicar el corpus).
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from nucleo.scripts.importar_opiniones import importar_a_bd
from webapp.apps.opiniones.models import Opinion
from webapp.apps.opiniones.pipeline import ArchivoOpinionesInvalido, leer_corpus, obtener_componentes

CORPUS_DEFECTO = settings.BASE_DIR / "datos" / "ejemplos" / "opiniones_ejemplo.csv"


class Command(BaseCommand):
    help = "Carga un corpus de ejemplo y lo clasifica (zero-shot) si la base está vacía."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--corpus", type=Path, default=CORPUS_DEFECTO)
        parser.add_argument(
            "--forzar",
            action="store_true",
            help="sembrar aunque ya existan opiniones (se omiten las repetidas)",
        )

    def handle(self, *args, **opciones) -> None:
        if Opinion.objects.exists() and not opciones["forzar"]:
            self.stdout.write("La base ya tiene opiniones; no se siembra nada.")
            return

        corpus_ruta: Path = opciones["corpus"]
        if not corpus_ruta.exists():
            raise CommandError(f"No existe el corpus de ejemplo: {corpus_ruta}")

        # `generar_propuestas` carga los modelos: se importa aquí y no arriba
        # para que `manage.py help` no pague el arranque de spaCy/embeddings.
        from nucleo.scripts.exportar_propuestas import generar_propuestas

        with corpus_ruta.open("rb") as archivo:
            try:
                corpus = leer_corpus(archivo)
            except ArchivoOpinionesInvalido as exc:
                raise CommandError(str(exc)) from exc

        componentes = obtener_componentes()
        propuestas = generar_propuestas(corpus, componentes.lematizador, componentes.clasificador)
        creadas_opinion, creadas_requisito = importar_a_bd(corpus, propuestas)

        self.stdout.write(
            self.style.SUCCESS(
                f"{creadas_opinion} opiniones sembradas "
                f"({creadas_requisito} en la cola de validación, todas como 'propuesto')."
            )
        )
