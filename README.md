---
title: ECO — Requisitos desde opiniones
emoji: 🔊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: ECO escucha las opiniones de Apklis y propone requisitos RF/RNF con validación humana
---

# ECO — Escucha Colectiva de Opiniones

**ECO** es el prototipo que implementa el *método de identificación de requisitos desde
opiniones de usuarios*: devuelve, en forma de requisitos, el eco de lo que dice la
multitud de usuarios de una tienda de aplicaciones.

Proyecto de tesis de Maestría en Informática Avanzada (UCI). Dado un conjunto de
opiniones de usuarios de **Apklis** (tienda nacional cubana de aplicaciones), clasifica
cada opinión como **Requisito Funcional (RF)**, **Requisito No Funcional (RNF)** o
**Ruido** mediante representación semántica contextual, con **validación humana
obligatoria** antes de aceptar cualquier resultado.

- **Autora:** Ing. Melany Coto Ramírez
- **Tutores:** Dr.C. Hubert Viltres Sala · MSc. Vladimir Milián Núñez

> La máquina propone, la persona decide. Ninguna clasificación se da por buena sin
> que un especialista la confirme o la corrija.

## El método (5 fases)

| Fase | Qué hace | Dónde vive |
|---|---|---|
| 1. Extracción | Recolecta opiniones de Apklis y anonimiza al autor | `nucleo/extraccion/` |
| 2. Preprocesamiento | Limpieza, jerga cubana (DNJL) y lematización con spaCy | `nucleo/preprocesamiento/` |
| 3. Representación | Embeddings contextuales; TF-IDF como línea base | `nucleo/representacion/` |
| 4. Clasificación | RF / RNF / Ruido con Scikit-Learn (o zero-shot) | `nucleo/clasificacion/` |
| 5. Validación | Cola de revisión humana en la web | `webapp/apps/validacion/` |

El método (`nucleo/`) **no depende de Django**: se ejecuta y se prueba sin la capa web.
La aplicación web es el envoltorio, no al revés.

## Resultado principal

Sobre el gold standard v1 (500 opiniones etiquetadas a mano), con semilla fija y el mismo
conjunto de prueba:

| Método | Precisión | Recall | F1 |
|---|---|---|---|
| TF-IDF + LogReg (línea base) | 0.8886 | 0.8300 | 0.8477 |
| **Semántico + LogReg** | **0.9121** | **0.9000** | **0.9050** |

Reproducible con un solo comando: `python scripts/baseline.py` → `resultados/baseline_v1.json`.

## Puesta en marcha local

```bash
python -m venv .venv && .venv/Scripts/activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements-lock.txt                # versiones exactas
python -m spacy download es_core_news_sm
cp .env.example .env                                # y rellenar DJANGO_SECRET_KEY y la base
python webapp/manage.py migrate
python webapp/manage.py createsuperuser
python webapp/manage.py runserver
```

Pruebas: `pytest` (requiere PostgreSQL en marcha para las pruebas de la webapp).

## Despliegue

Hay una imagen Docker lista (`Dockerfile`) pensada para un despliegue de demostración.
El procedimiento completo —incluido qué datos **no** salen de la máquina local— está en
[docs/DESPLIEGUE.md](docs/DESPLIEGUE.md).

## Documentación

| Documento | Contenido |
|---|---|
| [docs/PROYECTO.md](docs/PROYECTO.md) | Problema, hipótesis, método y evaluación |
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | Arquitectura propuesta, modelo de datos y hoja de ruta |
| [docs/ARQUITECTURA_ACTUAL.md](docs/ARQUITECTURA_ACTUAL.md) | Lo que el código hace **hoy**, módulo por módulo |
| [docs/bitacora-experimentos.md](docs/bitacora-experimentos.md) | Bitácora de experimentos y decisiones |
| [docs/GLOSARIO.md](docs/GLOSARIO.md) | Términos del dominio |

## Restricciones del proyecto

Solo software libre, modelos abiertos ejecutables **sin conexión** tras la descarga
inicial, opiniones anonimizadas, resultados reproducibles (semillas fijas y versiones
ancladas) y validación humana siempre presente.
