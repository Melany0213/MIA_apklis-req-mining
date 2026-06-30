# PROYECTO.md — Contexto ampliado de la tesis

Documento de referencia para Claude Code. El `CLAUDE.md` de la raíz resume lo esencial;
aquí está el detalle del problema, el método y la evaluación.

## 1. Problema y motivación

El desarrollo de software depende de la retroalimentación de los usuarios. En el ecosistema
móvil, las tiendas de aplicaciones concentran miles de opiniones espontáneas que contienen
reportes de fallos, quejas de rendimiento y solicitudes de nuevas funcionalidades. Esa
retroalimentación es una fuente legítima de requisitos (paradigma **CrowdRE**), pero:

- está dominada por lenguaje informal, ambiguo y con jerga local;
- alrededor del **90 % es ruido** irrelevante para el desarrollo;
- su volumen hace **inviable el análisis manual** y entierra los requisitos importantes.

En Cuba esto se cruza con la **soberanía tecnológica**: la tienda nacional **Apklis**
(Proyecto Z17) necesita herramientas propias para interpretar a sus usuarios, en su idioma,
sin depender de soluciones extranjeras.

## 2. Objetivo

Desarrollar un **método** —y un **prototipo web** que lo demuestre— para identificar y clasificar
automáticamente requisitos de software a partir de opiniones de usuarios de Apklis, distinguiendo
**RF / RNF / Ruido** mediante análisis semántico, con validación humana final.

- **Objeto de estudio:** el proceso de obtención de requisitos a partir de opiniones de usuarios.
- **Campo de acción:** dicho proceso en tiendas de aplicaciones nacionales.

## 3. Hipótesis y variables

**Hipótesis:** un método basado en **representación semántica contextual** eleva la calidad de la
clasificación de opiniones (mejor identificación de RF y RNF) frente a los enfoques tradicionales
basados en **frecuencia de palabras (TF-IDF)**.

- **Variable independiente:** el método de representación/clasificación (semántico vs. TF-IDF).
- **Variable dependiente:** la calidad de la clasificación (precisión, recall, F1).

Implicación para el código: **TF-IDF + ML clásico no es descartable**; es la línea base contra la
que se compara y debe quedar implementado y reproducible.

## 4. El método en detalle (las 5 fases)

### Fase 1 — Extracción
Recolección automatizada de opiniones desde Apklis (texto, fecha, calificación si existe,
aplicación asociada, versión). Salida: corpus crudo. Debe ser repetible y respetuoso con la
plataforma. Anonimizar al autor desde el inicio.

### Fase 2 — Preprocesamiento lingüístico
Con **spaCy (modelo en español)**: limpieza, normalización, tokenización y lematización.
**Adaptado al español de Cuba:** manejar jerga, errores ortográficos frecuentes, emojis y
abreviaturas. Esta adaptación es un aporte; no asumir un español "de manual".

### Fase 3 — Representación semántica contextual
Generar **embeddings** con un modelo preentrenado en español (Transformers /
Sentence-Transformers). Captura el significado más allá de la coincidencia léxica: reconoce que
"se traba", "se cae" y "deja de funcionar" expresan lo mismo. **Baseline paralelo:** vectorización
TF-IDF para la comparación de la hipótesis.

### Fase 4 — Clasificación semántica
Clasificador supervisado (Scikit-Learn) que asigna a cada opinión una de tres etiquetas:
`RF`, `RNF` o `Ruido`. Entrenar y evaluar tanto sobre embeddings semánticos como sobre TF-IDF
para comparar. Registrar versión de modelo y parámetros.

### Fase 5 — Validación
Un **especialista en ingeniería de requisitos** revisa la propuesta del clasificador, la confirma
o la corrige, y solo entonces el requisito pasa a la salida definitiva. Esta fase es obligatoria
(razón ética y de rigor) y debe quedar reflejada en la interfaz y en el modelo de datos
(estado del requisito: propuesto / validado / descartado).

### Alcance
La automatización cubre la **identificación y captura inicial**. No sustituye el análisis de
factibilidad, la negociación ni la priorización estratégica, que siguen siendo humanos.

## 5. Caso de estudio

La aplicación cliente de Apklis (alto número de descargas y miles de opiniones) sirve como caso de
validación. Ejemplo de extremo a extremo:

> "La app se cierra cada vez que intento subir una foto de perfil, deberían arreglarla."
> → preprocesamiento → embedding → clasificador: **RNF (estabilidad)** → especialista **valida** →
> requisito incorporado.

## 6. Evaluación

- **Gold standard:** subconjunto del corpus etiquetado manualmente como referencia.
- **Métricas:** precisión, exhaustividad (recall), F1; matriz de confusión por clase.
- **Comparación:** método semántico vs. TF-IDF sobre el **mismo** conjunto de prueba.
- **Criterio de éxito:** el método semántico supera a la línea base, en especial en recall
  (menos requisitos reales perdidos entre el ruido).
- Mantener el *test set* separado del entrenamiento y la evaluación reproducible (semillas, scripts).

## 7. Naturaleza académica (no es solo una app)

- Cada decisión técnica debe ser **explicable y defendible** ante el tribunal.
- **Reproducibilidad** ante todo: versiones ancladas, semillas fijas, datos y pasos documentados.
- Llevar **bitácora de experimentos** (`docs/bitacora-experimentos.md`): configuración, datos,
  resultados, conclusiones.
- Metodología de gestión: SCRUM con sprints; pero a nivel de código prima la modularidad, las
  pruebas y la trazabilidad de los experimentos.

## 8. Roles de usuario en el prototipo

- **Administrador:** gestiona usuarios, aplicaciones y corridas de extracción.
- **Especialista / Validador:** revisa y valida las clasificaciones (fase 5).
- (Opcional) **Analista:** consulta resultados y métricas, sin validar.
