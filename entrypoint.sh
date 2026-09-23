#!/bin/sh
# Arranque del contenedor: migrar, asegurar el usuario validador, sembrar el
# corpus de ejemplo (solo si la base está vacía) y levantar el servidor.
set -e

echo "==> Migraciones"
python webapp/manage.py migrate --noinput

echo "==> Usuario administrador"
python webapp/manage.py asegurar_admin

echo "==> Corpus de ejemplo"
# No es crítico: si falla (p. ej. falta el modelo en caché), el sistema debe
# levantar igual y permitir subir opiniones desde el navegador.
python webapp/manage.py sembrar_demo || echo "AVISO: no se pudo sembrar el corpus de ejemplo"

echo "==> Servidor en el puerto ${PORT:-7860}"
# --timeout 300: la primera petición que clasifica carga spaCy y el modelo de
# embeddings en memoria (decenas de segundos); con el timeout por defecto de
# gunicorn el worker moriría antes de responder.
exec gunicorn webapp.config.wsgi:application \
    --bind "0.0.0.0:${PORT:-7860}" \
    --workers "${WEB_CONCURRENCY:-1}" \
    --threads 4 \
    --timeout 300 \
    --access-logfile -
