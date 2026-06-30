# CLAUDE.md — Método de identificación de requisitos desde opiniones de usuarios

> Contexto permanente del proyecto. Léelo al inicio de cada sesión.
> Detalle ampliado en `docs/PROYECTO.md` (qué y por qué) y `docs/ARQUITECTURA.md` (cómo).
> Léelos cuando trabajes en el método, el modelo de datos o la evaluación.

## Qué es este proyecto

Tesis de Maestría en Informática Avanzada (UCI). Es a la vez **una contribución científica
(el método)** y **un prototipo funcional (la aplicación web)** que lo demuestra.

**Objetivo:** dado un conjunto de opiniones de usuarios de una tienda nacional de aplicaciones
(Apklis), clasificar automáticamente cada opinión como **Requisito Funcional (RF)**,
**Requisito No Funcional (RNF)** o **Ruido**, usando **representación semántica contextual**,
con **validación humana obligatoria** antes de aceptar cualquier resultado.

**Hipótesis a demostrar:** la representación semántica contextual mejora la calidad de la
clasificación frente al enfoque tradicional basado en frecuencia de palabras (TF-IDF).
Por eso TF-IDF + ML clásico se implementa como **línea base de comparación**, no se descarta.

- **Autora:** Ing. Melany Coto Ramírez
- **Tutores:** Dr.C. Hubert Viltres Sala · MSc. Vladimir Milián Núñez

## El método (5 fases) — es el núcleo científico

El pipeline va de opinión cruda a requisito validado:

1. **Extracción** — recolectar opiniones de Apklis → corpus.
2. **Preprocesamiento lingüístico** — limpieza, normalización y lematización con spaCy,
   adaptado al **español informal de Cuba** (jerga, errores ortográficos, emojis).
3. **Representación semántica contextual** — embeddings con Transformers /
   Sentence-Transformers (modelo preentrenado en español). Baseline: TF-IDF.
4. **Clasificación semántica** — clasificador (Scikit-Learn) → RF / RNF / Ruido.
5. **Validación** — un especialista confirma o corrige el requisito antes de la salida final.

Regla de oro: **la máquina propone, la persona decide.** La fase 5 nunca se omite ni se
automatiza. Ver detalle de cada fase en `docs/PROYECTO.md`.

## Stack tecnológico (fijo)

- **Python 3.12**
- **PLN/ML:** spaCy (es), Transformers, Sentence-Transformers, Scikit-Learn, NumPy, SciPy, Pandas
- **Web:** Django (patrón MTV) + Django REST Framework
- **Frontend:** Tailwind CSS (plantillas Django)
- **Datos:** PostgreSQL con el ORM de Django

## Restricciones que NO se negocian

Estas vienen del marco de la tesis (soberanía tecnológica y ética); cualquier código debe respetarlas:

- **Solo software libre.** Nada de servicios propietarios o de nube de pago. En concreto:
  **NO uses APIs externas tipo OpenAI / Google Cloud / Azure.** Todos los modelos deben ser
  abiertos y descargables, capaces de ejecutarse **localmente / en servidores nacionales, sin
  conexión** tras la descarga inicial.
- **Validación humana siempre presente.** No aceptes ni publiques clasificaciones sin el paso
  de validación. No añadas modos que "auto-aprueben".
- **Privacidad:** anonimiza las opiniones; no guardes datos personales identificables de los
  autores de las reseñas.
- **Reproducibilidad (es una tesis):** fija las semillas aleatorias, ancla las versiones de
  dependencias y deja scripts que reproduzcan los experimentos y las métricas. No inventes
  datos ni resultados. Registra cada experimento en `docs/bitacora-experimentos.md`.
- **El método va desacoplado de Django.** El pipeline vive en el paquete `nucleo/` y debe poder
  ejecutarse y probarse **sin** la capa web. La app web es el envoltorio, no al revés.

## Convenciones de código

- **PEP 8**, *type hints* en funciones públicas, y **docstrings y comentarios en español**.
- **Idioma de los identificadores:** nombres del dominio en español para coincidir con la tesis
  (`Opinion`, `Requisito`, `Clasificador`, `etiqueta`); el resto de utilidades técnicas en inglés
  si es lo idiomático. Sé consistente con lo que ya exista en el archivo.
- **Etiquetas del dominio canónicas (usar SIEMPRE estas, no sinónimos):** `RF`, `RNF`, `Ruido`.
- **Pruebas con `pytest`.** Toda lógica del `nucleo/` lleva pruebas. Métricas y pipeline también.
- **Configuración por variables de entorno** / settings de Django. **Nunca** secretos ni rutas
  absolutas embebidas en el código.
- **Commits** pequeños y descriptivos, en español, en presente ("agrega preprocesamiento es-CU").
- Migraciones de base de datos siempre vía Django (`makemigrations` / `migrate`).

## Evaluación (cómo se valida la hipótesis)

Sobre un subconjunto del corpus **etiquetado manualmente (gold standard)**, comparar el método
semántico contra la línea base TF-IDF con: **precisión, exhaustividad (recall) y F1**, más matriz
de confusión. El método semántico debe superar a TF-IDF en las tres. Mantener el conjunto de
prueba separado y reproducible.

## Estructura del repositorio

```
nucleo/        # EL MÉTODO (independiente de Django): extraccion, preprocesamiento,
               # representacion (semantica + tfidf), clasificacion, evaluacion, pipeline.py
webapp/        # Django (MTV) + DRF: apps opiniones, requisitos, validacion, usuarios
datos/         # corpus y gold standard (NO versionar datos sensibles; ver .gitignore)
notebooks/     # experimentos exploratorios
tests/         # pruebas pytest
docs/          # PROYECTO.md, ARQUITECTURA.md, GLOSARIO.md, bitacora-experimentos.md
```

Detalle de carpetas, modelo de datos y hoja de ruta en `docs/ARQUITECTURA.md`.

## Flujo de trabajo con el agente

- Trabaja **una funcionalidad a la vez** y verifica de extremo a extremo antes de darla por hecha.
- Antes de empezar algo no trivial, **propón un plan corto** y espera confirmación.
- Si una decisión afecta al método o a las métricas (es lo defendible en la tesis), **explícala**
  y déjala anotada en la bitácora.
- Cuando termines una fase, **actualiza** `docs/bitacora-experimentos.md` con qué se hizo y qué falta.

## Glosario rápido

RF = requisito funcional (qué debe hacer) · RNF = requisito no funcional (atributo de calidad:
rendimiento, estabilidad, usabilidad…) · Ruido = opinión sin información útil para requisitos ·
CrowdRE = ingeniería de requisitos basada en la multitud · Embedding = vector de significado ·
TF-IDF = línea base por frecuencia de palabras · Gold standard = subconjunto etiquetado a mano ·
Apklis = tienda nacional cubana de aplicaciones. Glosario completo en `docs/GLOSARIO.md`.
