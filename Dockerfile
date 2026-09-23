# Imagen de despliegue del prototipo (demostración en Hugging Face Spaces).
#
# Decisiones que afectan a la tesis, no cambiarlas sin anotarlas en la bitácora:
#  - Python 3.14 y las versiones EXACTAS de requirements-lock.txt: la imagen
#    debe ser el mismo entorno con el que se obtuvieron las métricas.
#  - torch en su variante CPU: el servidor no tiene GPU y las ruedas CUDA
#    añaden ~2 GB inútiles. No cambia el resultado del modelo, solo el tamaño.
#  - Los modelos de PLN (spaCy + embeddings) se descargan AQUÍ, en tiempo de
#    construcción, porque `nucleo/representacion/semantica.py` fuerza
#    HF_HUB_OFFLINE=1: en ejecución no se conecta a internet. Es la misma
#    restricción de soberanía tecnológica del proyecto — una vez construida,
#    la imagen clasifica sin salir a la red.
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    HF_HOME=/home/user/.cache/huggingface

# libpq5: cliente de PostgreSQL que necesita psycopg2 en ejecución.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios con UID 1000 (el que usa Hugging Face Spaces).
RUN useradd --create-home --uid 1000 user
WORKDIR /app

# 1) torch CPU primero, para que el lock no arrastre las ruedas CUDA.
RUN pip install --no-cache-dir torch==2.12.1 --index-url https://download.pytorch.org/whl/cpu

# 2) El resto del entorno, con versiones exactas. Se copian antes que el
#    código para no reinstalar 1.5 GB cada vez que cambia un .py.
COPY requirements-lock.txt pyproject.toml ./
COPY nucleo/__init__.py nucleo/__init__.py
RUN pip install --no-cache-dir -r requirements-lock.txt gunicorn==23.0.0

# 3) Modelos de PLN horneados en la imagen (ver cabecera).
RUN python -m spacy download es_core_news_sm
RUN mkdir -p /home/user/.cache/huggingface \
    && python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')" \
    && chown -R user:user /home/user/.cache

COPY . .

# Estáticos servidos por WhiteNoise. La clave de aquí es de usar y tirar:
# solo existe para que `collectstatic` pueda importar settings.py.
RUN DJANGO_SECRET_KEY=clave-solo-para-construir-la-imagen \
    python webapp/manage.py collectstatic --noinput \
    && chown -R user:user /app

USER user
EXPOSE 7860
ENTRYPOINT ["/app/entrypoint.sh"]
