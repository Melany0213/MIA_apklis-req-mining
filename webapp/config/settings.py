"""Configuración Django — lee valores desde variables de entorno (.env)."""

from pathlib import Path

from decouple import Csv, config

from nucleo.preprocesamiento.lematizador import MODELO_DEFECTO as _MODELO_SPACY_DEFECTO
from webapp.config.bd import desde_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost", cast=Csv())

# Despliegue detrás de un proxy que termina el TLS (HF Spaces, Render, Nginx):
# sin esto Django ve HTTP y rechaza el POST de validación por CSRF.
CSRF_TRUSTED_ORIGINS = config("DJANGO_CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
if config("DJANGO_DETRAS_DE_PROXY", default=False, cast=bool):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS deliberadamente apagado: en un dominio compartido (*.hf.space) la
    # cabecera afectaría también a sitios de terceros. Se activa cuando el
    # sistema viva en su propio dominio (servidor nacional).

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "webapp.apps.usuarios",
    "webapp.apps.opiniones",
    "webapp.apps.requisitos",
    "webapp.apps.validacion",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Sirve los estáticos desde el propio proceso (no hay Nginx en el
    # despliegue de demostración). Va inmediatamente después de Security.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "webapp.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "webapp" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "webapp.config.wsgi.application"

# Un entorno gestionado entrega la base como una sola DATABASE_URL; el
# entorno local sigue usando las variables DB_* de siempre (ver webapp/config/bd.py).
_DATABASE_URL = config("DATABASE_URL", default="")
DATABASES = {
    "default": desde_url(_DATABASE_URL)
    if _DATABASE_URL
    else {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="mia_db"),
        "USER": config("DB_USER", default="mia_user"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cu"
TIME_ZONE = "America/Havana"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    # Sesión de Django (misma autenticación que las vistas HTML) — sin JWT ni
    # tokens propios: la API comparte el login de /admin/login/.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Lectura pública por defecto (igual que las vistas HTML de solo lectura);
    # los endpoints que mutan datos (clasificar, validar) exigen
    # IsAuthenticated explícitamente en su vista/acción.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/validacion/"

# Semilla aleatoria para reproducibilidad de experimentos
SEMILLA_ALEATORIA: int = config("SEMILLA_ALEATORIA", default=42, cast=int)

# Rutas de modelos PLN. El default de MODELO_SPACY viene de
# nucleo.preprocesamiento.lematizador (única fuente de verdad, ver Fase 0 en
# la bitácora): no lo dupliques aquí con un valor distinto.
MODELO_SPACY: str = config("MODELO_SPACY", default=_MODELO_SPACY_DEFECTO)
MODELO_EMBEDDINGS: str = config(
    "MODELO_EMBEDDINGS",
    default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
MODELOS_DIR: Path = BASE_DIR / config("MODELOS_DIR", default="modelos")
