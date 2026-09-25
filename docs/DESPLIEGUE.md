# DESPLIEGUE.md — Poner el prototipo en línea

> Estado actual del prototipo, desplegado tal cual está, para poder enseñarlo y seguir
> construyendo encima. **No es el despliegue objetivo de la tesis**: ese es un servidor
> nacional, sin dependencias de nube extranjera (ver `docs/PROYECTO.md` §1 y
> `docs/ARQUITECTURA.md` §6). Lo de aquí es un espejo de demostración.

## Qué se despliega y qué no

| Sí viaja | No viaja (se queda en la máquina local) |
|---|---|
| Código de `nucleo/` y `webapp/` | `datos/corpus_crudo/` — opiniones reales extraídas |
| `datos/ejemplos/opiniones_ejemplo.csv` | `datos/gold_standard_privado/` — gold standard |
| Modelos abiertos (spaCy + embeddings), horneados en la imagen | `.env` con credenciales reales |

Lo excluye `.dockerignore`, que replica las mismas exclusiones del `.gitignore`. El
despliegue arranca con el corpus de ejemplo (4 opiniones) y se alimenta subiendo CSV/JSON
desde `/opiniones/subir/`.

## Arquitectura del despliegue

```
navegador ──HTTPS──► proxy del proveedor ──HTTP──► gunicorn (puerto 7860)
                                                      │
                                    WhiteNoise (estáticos) + Django
                                                      │
                                              PostgreSQL gestionado
```

Los modelos de PLN **no se descargan en ejecución**: `RepresentadorSemantico.cargar()`
fuerza `HF_HUB_OFFLINE=1`, así que el `Dockerfile` los descarga al construir la imagen.
Es la misma restricción de soberanía tecnológica del proyecto — una vez construida, la
imagen clasifica sin salir a internet.

## Procedimiento

### 1. Base de datos (Neon, plan gratuito)

1. Crear una cuenta en <https://neon.tech> y un proyecto PostgreSQL.
2. Copiar la cadena de conexión: `postgresql://usuario:clave@host.neon.tech/basededatos?sslmode=require`.

Esa URL entera va en la variable `DATABASE_URL`. Si no se define, el sistema cae a las
variables `DB_*` de siempre (entorno local) — ver [webapp/config/bd.py](../webapp/config/bd.py).

### 2. Espacio de ejecución (Hugging Face Spaces, plan gratuito)

1. Crear un Space en <https://huggingface.co/new-space> con **SDK: Docker** y visibilidad
   **privada** (la cola de validación exige login, pero el corpus y las métricas serían
   visibles en un Space público).
2. Crear un token de escritura en <https://huggingface.co/settings/tokens>
   (tipo *Write*). Hugging Face no acepta contraseña de cuenta por git: cuando el push
   pida credenciales, el usuario es el nombre de usuario de HF y la **contraseña es el
   token**.
3. Añadir el Space como remoto y empujar el repositorio:

   ```bash
   git remote add space https://huggingface.co/spaces/<usuario>/<nombre-del-space>
   git push space main
   ```

   Va el historial completo, no solo el último commit. Está comprobado que ningún commit
   del repositorio contiene el corpus crudo, el gold standard ni el `.env` (siempre
   estuvieron en `.gitignore`), así que el historial es publicable tal cual.

   El `README.md` de la raíz lleva la cabecera YAML que HF necesita (`sdk: docker`,
   `app_port: 7860`); no borrarla.

### 3. Secretos del Space

En *Settings → Variables and secrets*:

| Variable | Valor | Tipo |
|---|---|---|
| `DJANGO_SECRET_KEY` | 50 caracteres aleatorios | secreto |
| `DATABASE_URL` | la cadena de Neon | secreto |
| `DJANGO_SUPERUSER_USERNAME` | p. ej. `especialista` | variable |
| `DJANGO_SUPERUSER_PASSWORD` | clave larga | secreto |
| `DJANGO_DEBUG` | `False` | variable |
| `DJANGO_ALLOWED_HOSTS` | `<usuario>-<space>.hf.space` | variable |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://<usuario>-<space>.hf.space` | variable |
| `DJANGO_DETRAS_DE_PROXY` | `True` | variable |

Generar la clave secreta:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

`DJANGO_DETRAS_DE_PROXY` no es cosmético: activa las cookies seguras y hace que Django
reconozca el HTTPS del proxy. Sin él, validar desde el navegador falla por CSRF.

### 4. Qué ocurre en cada arranque

`entrypoint.sh`, en este orden:

1. `migrate` — aplica las migraciones.
2. `asegurar_admin` — crea el usuario validador si no existe. **No** pisa una contraseña
   cambiada a mano (solo con `--actualizar-clave`).
3. `sembrar_demo` — carga el corpus de ejemplo **solo si la base está vacía**, pasándolo
   por el mismo pipeline de fases 2-4 que la subida manual. Todo queda en estado
   `propuesto`: el despliegue nunca simula una validación humana que no ocurrió.
4. `gunicorn` con `--timeout 300` (la primera clasificación carga spaCy y los embeddings
   en memoria y eso tarda decenas de segundos).

## Probar la imagen en local antes de subirla

```bash
docker build -t eco .
docker run --rm -p 7860:7860 \
  -e DJANGO_SECRET_KEY=clave-de-prueba \
  -e DATABASE_URL='postgresql://eco_user:clave@host.docker.internal:5432/eco_db' \
  -e DJANGO_ALLOWED_HOSTS=localhost \
  -e DJANGO_SUPERUSER_USERNAME=especialista \
  -e DJANGO_SUPERUSER_PASSWORD=clave-de-prueba \
  eco
```

Luego abrir <http://localhost:7860/>. La construcción descarga torch y los modelos: la
primera vez tarda y ocupa unos 3 GB.

## Estado de verificación

| Comprobado | Cómo |
|---|---|
| Las 81 dependencias ancladas tienen rueda para Python 3.14 en Linux x86_64 | consulta a PyPI y al índice CPU de PyTorch, 2026-09-23 |
| El historial de git no contiene datos privados ni archivos pesados | `git log --all` sobre las rutas sensibles |
| La suite completa pasa (113 pruebas) y la CI está en verde | `pytest`, GitHub Actions |
| `manage.py check --deploy` sin avisos (salvo HSTS, apagado a propósito) | ejecución local |

**No comprobado todavía:** la imagen Docker nunca se ha construido (no hay Docker en la
máquina de desarrollo). El primer `docker build` —o la primera construcción del Space—
es la verificación que falta.

## Si no puedes conectar a la base desde tu máquina

Comprobado el 2026-09-24 desde la red de desarrollo: el puerto **5432 está filtrado**. La
conexión TCP se establece pero el `SSLRequest` de PostgreSQL nunca recibe respuesta, mientras
que el **mismo host por el 443 negocia TLS sin problema** — o sea, no es Neon ni es la
configuración del proyecto, es la red.

Consecuencias:

- **No afecta al despliegue.** El contenedor corre en la infraestructura del proveedor, que sí
  alcanza la base por 5432. Las migraciones las aplica `entrypoint.sh` al arrancar.
- **Sí impide probar contra la base gestionada desde local.** Para desarrollo se sigue usando
  el PostgreSQL local con las variables `DB_*`; `DATABASE_URL` solo se define en el Space.
- Para comprobar la cadena de conexión desde fuera del despliegue haría falta otra red.

Diagnóstico rápido, si vuelve a pasar en otro sitio:

```bash
python -c "import socket,ssl; h='<host>.neon.tech'
s=socket.create_connection((h,5432),timeout=15)
ssl.create_default_context().wrap_socket(s,server_hostname=h)"
```

Si eso se cuelga y con `443` en su lugar funciona, es filtrado de puerto, no la base.

## Limitaciones conocidas

- **El Space gratuito se duerme** tras 48 h sin visitas; la primera petición después
  tarda en despertar. Los datos no se pierden: viven en Neon, no en el contenedor.
- **El disco del contenedor es efímero.** Cualquier cosa que deba sobrevivir a un
  reinicio tiene que estar en la base de datos.
- **Tailwind entra por CDN** en `webapp/templates/base.html`: la interfaz necesita
  internet aunque el método no. Pendiente compilar Tailwind localmente antes de un
  despliegue realmente aislado.
- **Sin roles de usuario todavía.** Cualquier usuario autenticado puede validar o
  descartar (la app `usuarios/` está vacía, ver `docs/ARQUITECTURA_ACTUAL.md` §2).
- **Un solo worker** de gunicorn por defecto: cada worker carga su propia copia de los
  modelos en memoria. Subir `WEB_CONCURRENCY` solo si hay RAM de sobra.      
