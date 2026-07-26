# Bitácora de experimentos

Registro reproducible de cada experimento. Una entrada por corrida relevante. Mantenla al día:
es lo que sustenta la defensa de la tesis.

Plantilla de entrada:

---

## YYYY-MM-DD — Título corto del experimento

- **Objetivo:** qué se quería comprobar.
- **Datos:** corpus / subconjunto usado, tamaño, fuente, fecha de extracción.
- **Método/configuración:** representación (semántica/TF-IDF), modelo, hiperparámetros, semilla.
- **Resultados:** precisión / recall / F1 (por clase y global); matriz de confusión.
- **Comparación:** frente a la línea base u otra corrida.
- **Conclusión:** qué se aprendió y qué decisión se toma.
- **Pendiente:** próximos pasos.

---

## 2026-07-07 — Primeras corridas reales (TF-IDF vs. semántico) y pantalla de validación humana en la webapp

- **Objetivo:** (1) registrar en `/evaluacion/` las dos primeras corridas reales de
  clasificador sobre el gold standard v1, para tener el primer punto de comparación
  de la hipótesis de la tesis; (2) construir la parte de la webapp que faltaba para
  poder probar el sistema **a mano** (navegador), no solo por consola/pytest: listar
  el corpus y ejecutar la fase 5 (validación humana) opinión por opinión.
- **Datos:** `datos/gold_standard_privado/gold_standard_v1.csv` (500 filas) para las
  corridas; `datos/corpus_crudo/cu.uci.android.apklis.csv` +
  `..._propuestas.csv` (500 filas alineadas por índice) para poblar la cola de
  validación en la webapp.
- **Método/configuración:** nuevo script `nucleo/scripts/registrar_corrida.py`
  (glue reproducible entre `nucleo.clasificacion.{tfidf_logreg,semantico_logreg}` +
  `nucleo.evaluacion.metricas` y el modelo `CorridaEvaluacion`, sin lógica nueva de
  entrenamiento/evaluación — solo persiste el resultado). Split 80/20 estratificado,
  semilla 42, `class_weight="balanced"`, modelo semántico
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (ya cacheado
  localmente). Ambas corridas comparten exactamente el mismo split (mismo orden de
  argumentos en `train_test_split`, ver docstring de `semantico_logreg.entrenar`).
- **Resultados (corridas #4 y #5 en `/evaluacion/`):**
  - TF-IDF + LogReg: precisión 0.8886, recall 0.8300, F1 0.8477 (por clase — RF:
    F1 0.6154/soporte 7; RNF: F1 0.5517/soporte 9; Ruido: F1 0.8987/soporte 84).
  - Semántico + LogReg: precisión 0.9121, recall 0.9000, F1 0.9050 (por clase — RF:
    F1 0.6250/soporte 7; RNF: F1 0.6316/soporte 9; Ruido: F1 0.9576/soporte 84).
- **Comparación:** el método semántico supera a la línea base TF-IDF en las tres
  métricas globales (precisión, recall, F1) y en F1 por clase en las tres clases,
  consistente con la hipótesis de la tesis. **Con matices importantes:** el
  conjunto de prueba es pequeño y muy desbalanceado (test = 100 filas; soporte
  RF=7, RNF=9, Ruido=84), así que el F1 de RF y RNF descansa sobre muy pocos
  ejemplos — no tratar este resultado como concluyente, solo como primera señal.
- **Funcionalidad nueva (webapp):** apps `opiniones` y `validacion` (antes vacías)
  ahora tienen modelo, migración y pantalla:
  - `Opinion` (`webapp/apps/opiniones`) — corpus de solo lectura en `/corpus/`.
  - `Requisito` (`webapp/apps/validacion`) — cola de propuestas pendientes en
    `/validacion/` (filtrable por estado) y pantalla de decisión en
    `/validacion/<id>/` (login requerido; botones RF/RNF/Ruido, notas opcionales).
    Al validar se guarda `validado_por` (usuario autenticado) y `fecha_validacion`.
  - **Decisión de diseño:** se fusionaron en un solo modelo `Requisito` lo que
    `docs/ARQUITECTURA.md` §3 describe como dos entidades separadas
    (`Clasificacion` + `Requisito`), para no introducir dos tablas antes de que
    haya un caso de uso real que las necesite separadas (p. ej. guardar más de
    una propuesta por opinión). Revisar si hace falta separarlas cuando se
    comparen métodos de clasificación directamente sobre el corpus importado
    (hoy la comparación de métodos vive solo en `CorridaEvaluacion`, no aquí).
  - Import reproducible: `nucleo/scripts/importar_opiniones.py` carga corpus +
    propuestas a `Opinion`/`Requisito` con `estado="propuesto"` siempre — aunque
    el CSV de origen ya tenga `etiqueta_final` de una validación previa (como el
    gold standard), esa etiqueta **no** se reutiliza como si ya hubiera pasado
    por esta pantalla. Se importaron 498 de 500 filas (2 duplicadas por
    texto+autor idénticos).
  - Probado a mano end-to-end: login (`/admin/login/`), ver cola de pendientes,
    abrir una opinión, confirmar/corregir etiqueta, verificar que pasa a
    "validado" con usuario y fecha correctos, y que ya no aparece en pendientes.
- **Nota de nomenclatura (deuda existente, no corregida ahora):** la app Django
  `webapp/apps/requisitos` implementa en realidad el panel de *evaluación de
  experimentos* (`CorridaEvaluacion`, montado en `/evaluacion/`), no "propuestas y
  requisitos clasificados" como dice `docs/ARQUITECTURA.md` §2 — ese rol lo cubren
  ahora `opiniones`+`validacion`. No se renombró la app para no romper las
  migraciones/URLs ya existentes sin que se pida explícitamente.
- **Conclusión:** ya se puede recorrer el sistema completo a mano desde el
  navegador: `/corpus/` (fase 1-2 con propuesta de fase 4), `/validacion/` (fase 5)
  y `/evaluacion/` (comparación de corridas). Antes de esto solo `/evaluacion/`
  tenía pantalla, y estaba vacía.
- **Pendiente:** (1) correr más corridas (otros clasificadores: SVM, Random
  Forest, Naive Bayes, KNN, ya listados en `CLASIFICADORES` del modelo) para que
  la comparación TF-IDF vs. semántico no dependa de un solo par de corridas; (2)
  crecer el gold standard o usar un split menos desbalanceado para que el F1 de
  RF/RNF sea más confiable; (3) decidir si los 48 casos `revisar=SI` del gold
  standard (ver entrada 2026-07-04 más abajo) se resuelven antes de usarlo como
  conjunto de prueba definitivo; (4) considerar login con roles reales
  (`usuarios` app, hoy vacía) en vez de reusar el superusuario de Django admin.

---

## 2026-07-04 — Limpieza de datos de ejemplo y DNJL (Tabla 7)

- **Objetivo:** (1) quitar datos falsos del dashboard de evaluación antes de
  registrar corridas reales; (2) implementar el Diccionario de Normalización
  de Jerga Local (DNJL, Tabla 7 de la tesis) como módulo propio de la fase 2,
  con las 4 categorías de reglas exactas del documento.
- **Datos:** ninguno nuevo. Se confirmaron y borraron las 3 `CorridaEvaluacion`
  con `dataset="corpus_ejemplo_v1"` (ids 1–3, F1 0.73–0.86) que eran datos de
  ejemplo, no resultados de una corrida real.
- **Método/configuración:** `nucleo/preprocesamiento/dnjl.py` — mapeo directo
  por categoría (`neologismos_tecnologicos`, `abreviaturas_informales`,
  `errores_foneticos_ortograficos`, `lematizacion_verbos`) aplicado con una
  única expresión regular por límite de palabra (`\b...\b`, insensible a
  mayúsculas). Integrado en el orden limpieza → DNJL → lematización spaCy:
  se añadió a `nucleo/preprocesamiento/preprocesar()` y a
  `nucleo/evaluacion/muestra_validacion.generar_propuestas()` (antes, esta
  última solo aplicaba limpieza y pasaba el texto directo a los embeddings,
  sin DNJL ni lematización).
- **Decisión de diseño (no 100% explícita en el documento, a validar con el
  tutor si hace falta):** la categoría 4 del DNJL ("actualizando/actualicé/
  actualiza" → "actualizar") se solapa en la práctica con lo que ya hace el
  lematizador de spaCy sobre verbos regulares. Se implementó igual, tal cual
  la declara la Tabla 7 (mapeo directo, no delegado a spaCy), porque el
  documento la exige como regla propia del DNJL y porque cubre casos que
  spaCy podría lematizar distinto (p. ej. formas con tilde mal escrita).
  No se eliminó ni se fusionó con `lematizador.py`.
- **Resultados:** 40 pruebas pasan (`pytest -q`), incluyendo 15 casos
  parametrizados con los ejemplos literales de la Tabla 7, más límites de
  palabra, insensibilidad a mayúsculas y una frase completa con varias reglas
  a la vez.
- **Comparación:** N/A (no es un experimento de clasificación).
- **Conclusión:** el dashboard de evaluación ya no tiene datos falsos; el
  DNJL queda documentado, probado y conectado en los dos puntos donde el
  texto llega hoy a una capa de representación.
- **Pendiente:** (1) capa 5 formal de categorización aún no existe como
  componente separado; (2) módulo de validación humana (`webapp/apps/validacion`)
  sigue vacío — es la siguiente tarea, base para el gold standard; (3)
  confirmar con el tutor si la nomenclatura Tabla 6 (Capa de Ingesta, de
  Filtrado, de Incrustación, Predictiva, de Formalización) debe reflejarse
  también en nombres de código, o basta con el mapeo documentado en
  `docs/ARQUITECTURA.md` §2.1 (decisión tomada: solo documentar, no renombrar).

---

## 2026-07-03 — Extracción del corpus crudo: app "Apklis" (cu.uci.android.apklis)

- **Objetivo:** obtener un corpus real de opiniones para poder ejecutar las fases 2–5
  del método (preprocesamiento, representación, clasificación, evaluación) con datos
  reales en vez de sintéticos, de cara a la redacción del documento.
- **Datos:** 5900 reseñas públicas de la app "Apklis" (paquete `cu.uci.android.apklis`)
  descargadas vía `nucleo.extraccion.corpus` desde `https://api.apklis.cu/v2/review/`,
  con espera de 0.5s entre peticiones. Rango de fechas: 2018-03-14 a 2026-07-03.
  Guardado en `datos/corpus_crudo/cu.uci.android.apklis.csv` (no versionado).
- **Método/configuración:** `ClienteApklis.listar_opiniones` + `anonimizar_autor`
  (HMAC-SHA256, sal por defecto de desarrollo). 5865 autores anónimos únicos sobre
  5900 opiniones (algunos autores repiten). Distribución de calificación: 5★=1889,
  1★=1884, 2★=1129, 3★=516, 4★=482 — fuertemente bimodal (satisfacción/queja).
- **Observación de calidad de datos:** algunas opiniones contienen datos personales
  de terceros dentro del propio texto (p. ej. números de teléfono, ofertas ajenas a
  la app) que no son el autor de la reseña. La anonimización actual solo cubre el
  identificador del autor, no el contenido libre. A evaluar en fase 2 (preprocesamiento)
  si conviene enmascarar patrones de PII (teléfonos, correos) dentro del texto antes
  de almacenarlo, más allá de lo ya exigido para el autor.
- **Comparación:** N/A (primera extracción real; no hay corrida previa).
- **Conclusión:** hay volumen suficiente (5900 opiniones) para construir un gold
  standard y correr los experimentos comparativos semántico vs. TF-IDF.
- **Pendiente:** (1) decidir tamaño y método del gold standard etiquetado a mano
  (fase 5, requiere a un humano — no se puede generar solo); (2) implementar fase 2
  (preprocesamiento es-CU, actualmente `nucleo/preprocesamiento` está vacío); (3)
  implementar fase 4 (clasificación, actualmente `nucleo/clasificacion` está vacío);
  (4) correr `nucleo/evaluacion/metricas.py` sobre el gold standard para comparar
  semántico vs. TF-IDF una vez haya etiquetas reales.

---

## 2026-07-04 — Gold standard v1 (500 opiniones, validación humana completa)

- **Objetivo:** producir el primer gold standard etiquetado para poder entrenar
  y evaluar clasificadores supervisados (SVM/LogReg sobre TF-IDF y sobre
  embeddings semánticos), cumpliendo la fase 5 obligatoria del método
  (validación humana, no auto-aprobación).
- **Datos:** las 500 opiniones de `cu.uci.android.apklis` ya preprocesadas
  (limpieza → DNJL → lematización) y propuestas por el clasificador zero-shot
  (`nucleo/scripts/exportar_propuestas.py`), semilla 42, modelo
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- **Método/configuración:** la autora (especialista del dominio) revisó **las
  500 filas una por una** y decidió `etiqueta_final` (RF/RNF/Ruido) a partir de
  `etiqueta_propuesta` del zero-shot, aplicando su propio criterio de forma
  sistemática (p. ej. degradar alabanzas genéricas — "muy buena", "excelente" —
  a Ruido; reconocer patrones de atributo de calidad — "eficaz", "estable",
  "rápido" — como RNF; reconocer solicitudes/fallos de función concreta como
  RF). Las filas que la autora consideró dudosas quedaron marcadas
  `revisar=SI` como señal para una segunda opinión (p. ej. del tutor), no como
  indicador de que el resto no se revisó. Esto constituye la fase 5
  (validación humana) del método — no un reetiquetado automático.
- **Nota técnica (encoding):** el CSV corregido llegó con mojibake irreversible
  en emojis y mojibake recuperable en tildes/ñ (bytes UTF-8 releídos como
  Latin-1). Para no arrastrar ese problema al gold standard, `texto_original`,
  `texto_normalizado`, `etiqueta_propuesta` y `confianza` se tomaron del CSV ya
  generado y verificado en UTF-8 (`datos/corpus_crudo/
  cu.uci.android.apklis_propuestas.csv`), verificando fila a fila que
  `confianza` y `etiqueta_propuesta` coincidieran exactamente con el archivo
  corregido antes de fusionar; solo `etiqueta_final` y `revisar` se tomaron de
  ese archivo.
- **Resultados:** distribución de `etiqueta_final` — Ruido=417 (83.4%),
  RNF=46 (9.2%), RF=37 (7.4%); 48/500 (9.6%) marcadas `revisar=SI`.
  Comparado con `etiqueta_propuesta` del zero-shot (Ruido=377, RNF=92, RF=31),
  la revisión humana degradó bastantes RNF propuestos (alabanzas genéricas
  sin contenido de calidad) a Ruido.
- **Comparación:** N/A (primer gold standard; sin corrida de clasificador
  entrenado todavía que comparar).
- **Conclusión:** ya existe un gold standard v1 válido (validación humana
  completa, no parcial) para entrenar los clasificadores clásicos (TF-IDF) y
  semánticos que exige la hipótesis de la tesis.
- **Ubicación:** `datos/gold_standard_privado/gold_standard_v1.csv` (no
  versionado — el texto original de la opinión puede contener PII incidental
  de terceros, ver observación de calidad de datos del 2026-07-03).
- **Pendiente:** (1) entrenar Regresión Logística sobre TF-IDF con este gold
  standard; (2) entrenar Regresión Logística sobre los embeddings semánticos
  con este gold standard; (3) evaluar ambos con `nucleo/evaluacion/metricas.py`
  y comparar contra la hipótesis de la tesis; (4) considerar si los 48 casos
  `revisar=SI` deben resolverse con una segunda opinión (tutor) antes de
  congelar v1 como conjunto de prueba definitivo.

---
