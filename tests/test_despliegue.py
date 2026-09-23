"""Pruebas de la configuración de despliegue (DATABASE_URL y comandos de arranque).

El despliegue es infraestructura, no método — pero si falla, la fase 5 (la
validación humana) queda inaccesible, así que su lógica también se prueba.
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from webapp.apps.opiniones.models import Opinion
from webapp.config.bd import URLBaseDatosInvalida, desde_url

URL_GESTIONADA = "postgresql://usuario:clave@ep-demo-123.neon.tech:5432/mia_db"


def test_url_gestionada_se_traduce_a_la_config_de_django():
    config = desde_url(URL_GESTIONADA)

    assert config["ENGINE"] == "django.db.backends.postgresql"
    assert config["NAME"] == "mia_db"
    assert config["USER"] == "usuario"
    assert config["PASSWORD"] == "clave"
    assert config["HOST"] == "ep-demo-123.neon.tech"
    assert config["PORT"] == "5432"


def test_host_remoto_exige_tls_aunque_la_url_no_lo_diga():
    """Una base gestionada sin TLS expondría las opiniones en tránsito."""
    assert desde_url(URL_GESTIONADA)["OPTIONS"]["sslmode"] == "require"


def test_host_local_no_exige_tls():
    config = desde_url("postgresql://mia_user:clave@localhost:5432/mia_db")

    assert config["OPTIONS"]["sslmode"] == "disable"


def test_sslmode_explicito_de_la_url_manda():
    config = desde_url(f"{URL_GESTIONADA}?sslmode=verify-full")

    assert config["OPTIONS"]["sslmode"] == "verify-full"


def test_credenciales_con_caracteres_codificados():
    """Las claves generadas por los proveedores traen @, / y : codificados."""
    config = desde_url("postgresql://usuario:cl%40ve%2Frara@host.neon.tech/mia_db")

    assert config["PASSWORD"] == "cl@ve/rara"
    assert config["PORT"] == "5432"


@pytest.mark.parametrize(
    "url",
    [
        "mysql://usuario:clave@host/mia_db",
        "postgresql://usuario:clave@host/",
        "postgresql:///mia_db",
        "",
    ],
)
def test_url_invalida_falla_con_mensaje_claro(url):
    with pytest.raises(URLBaseDatosInvalida):
        desde_url(url)


@pytest.mark.django_db
def test_asegurar_admin_crea_el_usuario_desde_el_entorno(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "especialista")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "clave-de-prueba")

    call_command("asegurar_admin", stdout=StringIO())

    usuario = get_user_model().objects.get(username="especialista")
    assert usuario.is_superuser and usuario.is_staff
    assert usuario.check_password("clave-de-prueba")


@pytest.mark.django_db
def test_asegurar_admin_no_pisa_una_clave_cambiada_a_mano(monkeypatch):
    """Un reinicio del contenedor no debe revertir la contraseña del validador."""
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "especialista")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "clave-inicial")
    call_command("asegurar_admin", stdout=StringIO())

    usuario = get_user_model().objects.get(username="especialista")
    usuario.set_password("clave-nueva-elegida-por-la-persona")
    usuario.save()

    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "clave-inicial")
    call_command("asegurar_admin", stdout=StringIO())

    usuario.refresh_from_db()
    assert usuario.check_password("clave-nueva-elegida-por-la-persona")


@pytest.mark.django_db
def test_asegurar_admin_sin_entorno_no_crea_nada(monkeypatch):
    monkeypatch.delenv("DJANGO_SUPERUSER_USERNAME", raising=False)
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)

    call_command("asegurar_admin", stdout=StringIO())

    assert not get_user_model().objects.exists()


@pytest.mark.django_db
def test_sembrar_demo_no_duplica_si_ya_hay_corpus():
    """Se invoca en cada arranque del contenedor: debe ser inofensivo.

    Si intentara sembrar cargaría spaCy y los embeddings; que la prueba pase
    en menos de un segundo confirma que ni siquiera lo intenta.
    """
    Opinion.objects.create(texto_original="la app se cierra sola", aplicacion="Apklis")
    salida = StringIO()

    call_command("sembrar_demo", stdout=salida)

    assert Opinion.objects.count() == 1
    assert "no se siembra" in salida.getvalue()
