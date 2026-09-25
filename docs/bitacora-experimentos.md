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

## 2026-08-01 — Redundancia del catálogo de candidatos: TF-IDF vs. semántico

- **Objetivo:** cuantificar la redundancia (opiniones distintas que en
  realidad piden lo mismo) dentro de los requisitos candidatos, comparando la
  representación TF-IDF contra la semántica contextual — otro argumento a
  favor de la hipótesis central, además de precisión/recall/F1.
- **Script:** `nucleo/evaluacion/redundancia.py` (nuevo, independiente del
  pipeline; reutiliza el vectorizador TF-IDF ya ajustado en
  `datos/modelos/tfidf_logreg.joblib` y el mismo modelo Sentence-Transformers
  `paraphrase-multilingual-MiniLM-L12-v2` del resto del proyecto). Pruebas en
  `tests/test_evaluacion_redundancia.py`.
- **Datos:** los candidatos son las filas de `gold_standard_v1.csv` con
  `etiqueta_final` en {RF, RNF} — **83 opiniones** (37 RF + 46 RNF), sin
  Ruido. `id_opinion` es la posición de fila en ese CSV (no hay id propio).
- **Método:** para cada representación, `AgglomerativeClustering(metric=
  'cosine', linkage='average', n_clusters=None)` barriendo
  `distance_threshold` de 0.10 a 0.60 (paso 0.05). Tasa de redundancia =
  `1 - grupos/83`.
- **Resultados (tabla completa en
  `datos/gold_standard_privado/redundancia_umbrales.csv`):**

  | umbral | grupos TF-IDF | tasa TF-IDF | grupos semántico | tasa semántico |
  |--------|---------------|-------------|------------------|-----------------|
  | 0.10   | 83            | 0.0000      | 81               | 0.0241          |
  | 0.15   | 83            | 0.0000      | 73               | 0.1205          |
  | 0.20   | 83            | 0.0000      | 63               | 0.2410          |
  | 0.25   | 83            | 0.0000      | 58               | 0.3012          |
  | 0.30   | 83            | 0.0000      | 51               | 0.3855          |
  | 0.35   | 81            | 0.0241      | 44               | 0.4699          |
  | 0.40   | 79            | 0.0482      | 36               | 0.5663          |
  | 0.45   | 79            | 0.0482      | 26               | 0.6867          |
  | 0.50   | 78            | 0.0602      | 20               | 0.7590          |
  | 0.55   | 75            | 0.0964      | 15               | 0.8193          |
  | 0.60   | 73            | 0.1205      | 11               | 0.8675          |

  Similitud de coseno media entre pares: TF-IDF 0.0494, semántico 0.3729
  (los vectores TF-IDF son casi ortogonales entre sí incluso para
  paráfrasis, por la dispersión léxica del corpus).
- **Umbral operativo elegido: 0.30.** Es el punto donde TF-IDF todavía no
  detecta ninguna redundancia (tasa 0.0000, sigue viendo 83 candidatos
  únicos) mientras el semántico ya agrupa un 38.55% del catálogo (51 grupos).
  Se inspeccionó manualmente el fichero exportado en ese umbral
  (`datos/gold_standard_privado/redundancia_grupos_semantico.txt`) y los
  grupos formados son parafraseos genuinos del mismo requisito (p. ej. "no me
  deja abrir" / "no me deja descargarla" / "no me deja descargar"; "es muy
  eficaz" / "muy eficiente" / "buena y eficiente") y no candidatos distintos
  fundidos por error. Un umbral menor detecta muy poca redundancia real; uno
  mayor (≥0.40) empieza a fusionar quejas de rendimiento distintas (lentitud,
  cierres, errores de pago) en el mismo grupo, lo que sería sobre-fusión.
- **A ese umbral (0.30):** tasa de redundancia TF-IDF = **0.0000** (83
  grupos), tasa de redundancia semántico = **0.3855** (51 grupos). El
  semántico revela redundancia oculta para el léxico que TF-IDF no puede ver.
- **Agrupamiento manual de referencia:** no se ha construido todavía; el
  script acepta `--agrupamiento-manual <csv con id_opinion,id_grupo>` y
  calcula automáticamente índice de Rand ajustado, homogeneidad y
  completitud de cada representación contra él cuando se le pase uno.
- **Conclusión:** a un umbral conservador (0.30), la representación semántica
  ya detecta redundancia sustancial e interpretable en el catálogo de
  candidatos que la línea base TF-IDF no ve en absoluto — evidencia adicional
  a favor de la hipótesis central de la tesis.
- **Pendiente:** (1) decidir si se construye un agrupamiento manual de
  referencia (costoso: requiere revisar 83×82/2 pares o al menos los grupos
  candidatos) para poder reportar ARI/homogeneidad/completitud reales en la
  tesis; (2) si se amplía el gold standard, repetir el barrido para ver si
  0.30 se mantiene como punto de equilibrio.

---

## 2026-08-02 — Orquestador `nucleo/pipeline.py`, estado "descartado" y API REST mínima

- **Objetivo:** cerrar tres huecos entre lo documentado (CLAUDE.md,
  `docs/PROYECTO.md`, `docs/ARQUITECTURA.md`) y lo implementado: (1) el
  método no se podía invocar como un solo objeto sin pasar por scripts CLI;
  (2) la fase 5 no tenía forma de descartar una opinión no aprovechable sin
  forzarla a "Ruido"; (3) los endpoints REST de `docs/ARQUITECTURA.md` §4
  eran solo diseño orientativo, nunca código. Plan completo en
  `elegant-wondering-yeti.md` (histórico de la sesión).
- **Fase 1 — `nucleo/pipeline.py`:** `Pipeline.preparar()`/`ejecutar()`
  implementados de verdad (antes `NotImplementedError`). Preprocesa
  (`nucleo.preprocesamiento.preprocesar`), representa y clasifica una lista
  de opiniones. Sin `ruta_modelo`, `metodo="semantico"` cae a
  `ClasificadorZeroShot` (sin entrenar); `metodo="tfidf"` exige un
  clasificador ya entrenado (`ruta_modelo` a un `.joblib` de
  `nucleo.clasificacion.{tfidf_logreg,semantico_logreg}`) porque TF-IDF
  necesita un vocabulario ajustado de antemano — no se inventó un
  "TF-IDF zero-shot". `Propuesta.metodo` se amplió a
  `Literal["zero_shot", "semantico", "tfidf"]` para usar el mismo vocabulario
  que `Requisito.METODOS_PROPUESTA`. Pruebas en `tests/test_pipeline.py` (6
  casos, dobles de prueba, sin cargar spaCy/embeddings reales).
- **Fase 2 — estado "descartado":** `Requisito.ESTADOS` gana
  `("descartado", "Descartado")` (migración
  `0002_alter_requisito_estado.py`). Nueva vista `descartar` (
  `webapp/apps/validacion/views.py`), URL `<pk>/descartar/`, pestaña y
  columna condicional en `cola.html`, botón en `detalle.html`. Un requisito
  descartado deja `etiqueta_final` vacío (no se fuerza a ninguna de las 3
  etiquetas — "Ruido" sigue siendo una etiqueta final válida para opiniones
  sí evaluadas). Se extrajo `_registrar_decision()` para no duplicar la
  lógica de guardado entre `validar`, `descartar` y la acción `validar` de
  la API. Pruebas en `tests/test_validacion_descartar.py` (3 casos).
- **Fase 3 — API REST (DRF):** implementados los 5 endpoints de
  `docs/ARQUITECTURA.md` §4: `GET /api/opiniones/` (filtrable por
  `?aplicacion=`), `POST /api/clasificar/`, `GET /api/requisitos/?estado=`,
  `POST /api/requisitos/{id}/validar/`, `GET /api/evaluacion/`. Dos ajustes
  de seguridad respecto al texto orientativo original: `POST
  /api/clasificar/` usa el `Pipeline` de la fase 1 (vía
  `webapp/apps/opiniones/pipeline.py::obtener_pipeline`, cacheado por
  proceso) y no persiste nada — devuelve propuestas, igual que exige la
  regla de oro del método; `POST /api/requisitos/{id}/validar/` exige sesión
  autenticada (`IsAuthenticated`), igual que la vista web equivalente. Nuevo
  bloque `REST_FRAMEWORK` en `webapp/config/settings.py`
  (`SessionAuthentication` + `AllowAny` por defecto, permisos más
  restrictivos declarados por vista). Cada app registra su router DRF en su
  propio `urls.py` (`api_urlpatterns`); `webapp/config/urls.py` los agrupa
  bajo `/api/`. Pruebas en `tests/test_api_{opiniones,clasificar,validacion,
  evaluacion}.py` (10 casos, `rest_framework.test.APIClient`).
- **Fuera de alcance (decisión explícita):** no se tocó la fusión
  `Requisito`/`Clasificacion` (ya decidida el 2026-07-07), no se creó un
  modelo `Aplicacion` propio (implicaría migrar `Opinion.aplicacion` de
  `CharField` a FK con backfill), no se implementaron roles de usuario
  (`usuarios` app sigue vacía) ni management commands de Django (los scripts
  de `nucleo/scripts/*.py` ya cubren ese rol vía `python -m`).
- **Resultados:** suite completa en verde, `pytest -q` →
  **80 passed** (61 previas de la sesión + 19 nuevas de esta entrega:
  6 pipeline + 3 descartar + 10 API), sin regresiones. `python webapp/manage.py
  check` sin errores.
- **Conclusión:** el método ya se puede invocar como un solo objeto
  (`Pipeline`) sin depender de la capa web, la fase 5 distingue "descartado"
  de "Ruido" tal como describe `docs/PROYECTO.md`, y la API REST documentada
  en `docs/ARQUITECTURA.md` es código real y probado, no solo diseño.
- **Pendiente:** (1) decidir si `POST /api/clasificar/` debe poder recibir
  `ruta_modelo`/usar un clasificador entrenado en vez de zero-shot siempre;
  (2) roles de usuario reales para diferenciar permisos de validación de los
  de solo lectura en la API (hoy cualquier usuario autenticado puede validar
  o descartar); (3) documentar los nuevos endpoints en un lugar visible para
  quien continúe el prototipo (hoy solo están en el código y en esta
  entrada).

---

## 2026-08-14 — Validación humana completa del lote importado (498 opiniones)

- **Objetivo:** completar la fase 5 sobre las 498 opiniones importadas en
  `/validacion/` (distintas del gold standard v1), de cara a una presentación
  con la cola de pendientes en cero.
- **Método:** la especialista (autora) tomó **todas** las decisiones de
  etiqueta final, opinión por opinión — RF/RNF/Ruido o descartar. Para
  agilizar el mecanismo (no el criterio), se apoyó en asistencia de Claude
  Code para: extraer lotes de opiniones pendientes de la base de datos,
  aplicar sus decisiones ya tomadas, y señalar de forma automática patrones
  de "elogio corto sin señal" (candidatos claros a Ruido) para que la
  especialista confirmara en bloque en vez de leer cada uno. Ningún texto se
  clasificó sin que la especialista diera la etiqueta explícitamente; se
  rechazó explícitamente una primera petición de auto-validar el lote
  completo sin revisión, por violar la regla de oro del método (ver
  CLAUDE.md, "la máquina propone, la persona decide").
- **Hallazgo de proceso:** una auditoría automática sobre las filas ya
  validadas (buscando el mismo patrón "elogio corto sin señal" pero
  etiquetado RF/RNF) encontró 5 casos de error de captura (misclicks o,
  en un caso, un error propio al probar la API con datos reales): id 346
  ("excelente, muchas gracias"), 174, 157, 212 y 481 — todas corregidas a
  Ruido tras confirmarlo. Vale la pena repetir este tipo de auditoría después
  de cualquier sesión de validación rápida.
- **Criterios aplicados:** ver la nueva sección "Criterios operativos de
  validación (fase 5)" en `docs/GLOSARIO.md` — resume las reglas que se
  fueron fijando en esta sesión (palabras de atributo de calidad → RNF
  aunque sean elogio; quejas de lentitud sin culpar a la red → RNF; pedidos
  de más apps en el catálogo → Ruido; fallos funcionales concretos aunque el
  texto sea corto → RF; texto sin sentido o con PII incidental → descartar,
  no Ruido).
- **Resultados:** de 498 filas — **497 validadas, 1 descartada** (la
  descartada es de una prueba manual anterior, no de este lote). Distribución
  de `etiqueta_final`: Ruido 464 (93.2%), RF 27 (5.4%), RNF 6 (1.2%) —
  proporción de Ruido más alta que en el gold standard v1 (83.4%), esperable
  porque este lote no pasó por el muestreo estratificado por calificación del
  gold standard.
- **Conclusión:** cola de `/validacion/` en cero real (no simulado). El
  botón de la pestaña "Descartados" se quitó de `cola.html` por tener un solo
  caso no representativo — la funcionalidad de descartar sigue intacta
  (modelo, vista, API), solo no tiene su propio enlace de navegación por
  ahora.
- **Pendiente:** (1) revisar si el criterio "más apps en el catálogo → Ruido"
  se sostiene si aparece con más frecuencia en corpus futuros; (2) refinar el
  diccionario DNJL con los patrones de jerga/errores vistos en este lote
  (pendiente, se trabajará gradualmente); (3) decidir si se re-agrega un
  enlace a "Descartados" en la interfaz cuando haya más casos reales.

---

## 2026-08-19 — Fase 0 de escalado: auditoría del estado actual + red de seguridad

- **Objetivo:** antes de escalar el prototipo, (1) documentar lo que el
  código realmente hace hoy (no lo declarado), (2) fijar un experimento
  reproducible de referencia, (3) cubrir con pruebas lo que aún no estaba
  cubierto, (4) automatizar las pruebas en cada push, (5) anclar versiones
  exactas de dependencias. **No se cambió comportamiento del método** — todo
  lo de esta entrada es documentación, scripts, pruebas e infraestructura.
- **`docs/ARQUITECTURA_ACTUAL.md` (nuevo):** mapa módulo por módulo con la
  responsabilidad real de cada archivo de `nucleo/` y `webapp/`, diagrama
  Mermaid del flujo de datos, lista explícita de todo lo acoplado a Apklis/
  apps móviles (URLs y campos de `extraccion/apklis.py`, prototipos de
  `zero_shot.py`, branding `apklis-*` en las plantillas), y tabla de
  dependencias con versión exacta. Hallazgos que quedaron anotados ahí
  (no corregidos en esta fase, son decisiones de fases futuras):
  - `Lematizador.MODELO_DEFECTO="es_core_news_sm"` no coincide con el
    `MODELO_SPACY="es_core_news_md"` que usan `webapp/config/settings.py` y
    `nucleo/pipeline.py` — hay que tener ambos modelos descargados o unificar.
  - `requirements-lock.txt` traía `-e d:\proyectos\mia` (ruta absoluta de
    esta máquina) — corregido en esta misma entrada (ver más abajo).
  - `files (1).zip` commiteado en la raíz del repo (copia vieja de los docs
    de contexto) — ruido, no se borró sin confirmarlo primero.
  - Pie de página de `base.html` dice "Python 3.14 · Django 6", CLAUDE.md
    fija Python 3.12 — texto de UI incorrecto, sin efecto en runtime.
  - App `usuarios` sigue vacía: no hay roles reales, cualquier usuario
    autenticado puede validar/descartar vía la API (ya sabido, ver entrada
    2026-08-02).
- **`scripts/baseline.py` (nuevo):** reproduce el experimento principal de la
  tesis end-to-end (entrena TF-IDF+LogReg y semántico+LogReg sobre
  `datos/gold_standard_privado/gold_standard_v1.csv`, mismo split que
  `nucleo/clasificacion/{tfidf_logreg,semantico_logreg}`, semilla 42 fija) y
  añade la tasa de redundancia (umbral 0.30, ya justificado en la entrada
  2026-08-01) de cada representación. Escribe `resultados/baseline_v1.json`.
  Corrida real:
  - TF-IDF + LogReg: precisión 0.8886, recall 0.8300, F1 0.8477, redundancia
    0.0000 (83 grupos de 83 candidatos).
  - Semántico + LogReg: precisión 0.9121, recall 0.9000, F1 0.9050,
    redundancia 0.3855 (51 grupos de 83 candidatos).
  Cifras consistentes con las ya registradas en la entrada 2026-07-07 (mismo
  gold standard, misma semilla) — sirve como corrida de referencia
  reproducible con un solo comando, no un experimento nuevo.
- **Pruebas nuevas:**
  - `tests/test_preprocesamiento.py` — 5 casos borde añadidos a
    `preprocesar()`: texto vacío, solo espacios, solo signos de puntuación
    (spaCy descarta los tokens de puntuación → cadena vacía, no error), todo
    en mayúsculas (con DNJL de por medio) y solo emoji.
  - `tests/test_clasificacion_zero_shot_modelo_real.py` (nuevo) — a
    diferencia de `test_clasificacion_zero_shot.py` (dobles de prueba, rápido
    y determinista), esta prueba carga el modelo real de embeddings y el
    diccionario `PROTOTIPOS` de producción, y confirma que 6 opiniones
    inequívocas (2 por clase) se clasifican como se espera. Requiere el
    modelo cacheado localmente (ya lo estaba). El DNJL ya tenía cobertura
    completa (los 15 términos, límites de palabra, mayúsculas, frase
    completa) desde la entrada 2026-07-04 — no hizo falta añadir nada ahí.
  - Total: 74 pruebas de `nucleo/` + `scripts/` en verde sin tocar la base de
    datos (no se corrió la suite completa con Postgres en esta sesión; las
    pruebas de la API/validación que sí requieren DB no se tocaron y se
    dejan a cargo de la nueva CI, que sí levanta Postgres).
- **`.github/workflows/tests.yml` (nuevo):** corre `pytest` en cada push y
  pull request — servicio Postgres 16, spaCy `es_core_news_sm` descargado en
  el job, caché de pip y del caché de Hugging Face/spaCy para no repetir la
  descarga de ~500MB (torch + el modelo de embeddings) en cada corrida.
- **Dependencias:** `requirements-lock.txt` ya estaba anclado a versión
  exacta (era la única rota por la ruta absoluta, ya corregida); se replicó
  el mismo anclaje en `pyproject.toml` (antes con mínimos `>=`), para que la
  instalación normal (`pip install -e .`) y la reproducible
  (`pip install -r requirements-lock.txt`) queden consistentes.
- **Conclusión:** el método (`nucleo/`) está mejor probado y documentado de
  lo que sugería `docs/ARQUITECTURA.md` (que es la versión aspiracional) —
  las 5 fases funcionan de extremo a extremo y ya tenían una suite
  razonable; el trabajo de esta fase fue cerrar huecos puntuales (casos
  borde de preprocesamiento, el clasificador con el modelo real, CI,
  reproducibilidad de dependencias) y dejar por escrito, con nombres de
  archivo y línea, todo lo acoplado a Apklis para la fase de generalización
  que sigue.
- **Pendiente:** (1) decidir qué hacer con la inconsistencia
  `es_core_news_sm` vs. `es_core_news_md`; (2) limpiar `files (1).zip`
  (pedir confirmación antes de borrar); (3) corregir el pie de página con la
  versión de Python; (4) cuando se generalice el dominio (fuera de Apklis),
  los puntos de `docs/ARQUITECTURA_ACTUAL.md` §4 son la lista de partida.

---

## 2026-08-19 — Cierre del punto 1 de la Fase 0: modelo de spaCy unificado y límite de procedencia del gold standard documentado

- **Objetivo:** resolver el punto bloqueante detectado en el cierre de la Fase 0
  (entrada anterior, "Pendiente" (1)): `nucleo/pipeline.py` y
  `webapp/config/settings.py` declaraban su propio default de spaCy
  (`"es_core_news_md"`), distinto del de `nucleo/preprocesamiento/lematizador.py`
  (`"es_core_news_sm"`) — y `es_core_news_md` nunca estuvo instalado en este
  proyecto. Cualquier código que dependiera de ese default sin anularlo
  explícitamente habría fallado con `OSError [E050]` en un entorno limpio.
- **Investigación (antes de cambiar nada, como se pidió):**
  - Se confirmó con `spacy validate` que `es_core_news_sm` es, y siempre ha sido en
    este entorno, el único modelo de spaCy instalado.
  - Se rastreó el valor *efectivo* (no el declarado) de cada punto de entrada:
    `nucleo/pipeline.py` → `Pipeline()` sin argumentos habría fallado (nunca se
    ejercitó "en limpio": los tests que usan `Pipeline()` monkeypatchean
    `_crear_lematizador`); la webapp (`obtener_componentes()`/`obtener_pipeline()`)
    resuelve `es_core_news_sm` en la práctica porque el `.env` real fija
    `MODELO_SPACY=es_core_news_sm`, sobrescribiendo el default divergente de
    `settings.py`; `nucleo/scripts/exportar_propuestas.py` sin `--modelo-spacy` cae
    también en `es_core_news_sm` (fallback a `Lematizador()` sin argumentos).
  - Se determinó que **ni `nucleo/scripts/registrar_corrida.py`** (el script que
    generó los F1 originales de la tesis: TF-IDF 0.8477, semántico 0.9050, entrada
    2026-07-07) **ni `scripts/baseline.py` invocan spaCy en absoluto** — ambos leen
    directamente la columna `texto_normalizado` ya congelada en
    `gold_standard_v1.csv`. Por tanto la inconsistencia de defaults **no contaminó**
    ninguna métrica ya registrada, y `baseline_v1.json` se mantiene válido sin
    regenerar — el experimento comparativo sm/md quedó cancelado por esta misma
    razón (no hay nada que comparar: `baseline.py` no relematiza).
- **Corrección aplicada:**
  - `nucleo/preprocesamiento/lematizador.py` (`MODELO_DEFECTO = "es_core_news_sm"`)
    queda como única fuente de verdad. `nucleo/pipeline.py` y
    `webapp/config/settings.py` ahora lo **reexportan** (`from
    nucleo.preprocesamiento.lematizador import MODELO_DEFECTO as ...`) en vez de
    declarar su propio literal — ya no hay dos defaults que puedan divergir.
  - `.env.example`: `MODELO_SPACY` corregido a `es_core_news_sm` (antes decía
    `es_core_news_md`, incorrecto), con comentario explicando por qué no cambiarlo
    sin documentarlo.
  - Pruebas nuevas: `tests/test_pipeline_modelo_real.py` (marcada
    `@pytest.mark.modelo_real`, registrada en `pyproject.toml`) instancia
    `Pipeline()` **sin monkeypatch**, con spaCy y el modelo de embeddings reales, y
    confirma que procesa una opinión de extremo a extremo — es la prueba que habría
    detectado el `OSError [E050]` original, que ningún test anterior podía ver
    porque todos evitaban cargar spaCy real. `tests/test_config_modelo_spacy.py`
    falla si `nucleo.pipeline.MODELO_SPACY_DEFECTO` o el default de
    `webapp/config/settings.py` vuelven a divergir del de `lematizador.py`, y si
    `MODELO_SPACY` en el entorno real apunta a otro modelo sin documentarlo.
- **Límite de procedencia del gold standard (no se pudo resolver, es un límite de
  los datos, no del código — documentado también en
  `docs/ARQUITECTURA_ACTUAL.md` §7):**
  - La columna `texto_normalizado` de `gold_standard_v1.csv` está congelada desde
    el **2026-07-04** y se generó con `nucleo/scripts/exportar_propuestas.py`
    (bitácora, entrada "Gold standard v1").
  - **No consta registro del comando exacto que se ejecutó, del modelo de spaCy
    empleado ni de la versión del DNJL vigente esa fecha.** No hay bitácora de
    comandos, ni notebook, ni entrada de git con esa granularidad (el historial de
    git de este repo está en commits grandes y posteriores a las fechas de la
    bitácora, así que tampoco sirve como prueba cronológica).
  - **La evidencia disponible apunta a `es_core_news_sm`** (único modelo instalado
    en este proyecto en cualquier momento verificable, único fallback del script
    sin `--modelo-spacy`, valor fijado en el `.env` real) **sin ninguna evidencia a
    favor de `es_core_news_md`.** No es prueba irrefutable — no se puede descartar
    al 100% que se haya usado e instalado `md` puntualmente y luego desinstalado
    sin dejar rastro.
  - **Los resultados de la tesis son reproducibles a partir de `texto_normalizado`**
    (`scripts/baseline.py` lo demuestra: semilla fija, mismo split, mismas cifras
    que la corrida original) — **pero la columna `texto_normalizado` en sí no es
    reproducible desde `texto_original`** con el código actual, porque no quedó
    registrada la configuración exacta con la que se generó.
  - **Consecuencia práctica:** cualquier corpus que se genere de ahora en adelante
    debe registrar su procedencia completa junto al CSV (comando, modelo de spaCy
    efectivo, fecha) — este es el requisito que motiva la siguiente tarea
    (metadatos de `exportar_propuestas.py`).
- **Conclusión:** el punto bloqueante queda cerrado — ya no hay defaults de spaCy
  divergentes en el código, hay una prueba que lo garantiza, y la limitación real
  (procedencia no registrada del gold standard) queda documentada explícitamente
  en vez de asumida o escondida. `baseline_v1.json` no se tocó: sigue siendo la
  línea base válida de la tesis.
- **Pendiente:** (1) decidir si vale la pena reconstruir manualmente, con la
  especialista, una muestra de `texto_normalizado` a partir de `texto_original`
  con `es_core_news_sm` actual y comparar contra lo congelado, como evidencia
  indirecta adicional (no seguro que valga el esfuerzo); (2) los pendientes ya
  anotados en la entrada anterior (limpiar `files (1).zip`, pie de página con
  versión de Python) siguen abiertos, no se tocaron en esta entrada.

---

## 2026-09-22 — Despliegue del prototipo (imagen Docker + entorno gestionado)

- **Objetivo:** poner en línea el prototipo **tal como está hoy**, para poder
  enseñarlo y seguir construyendo encima, sin tocar el método. Nada de esta
  entrada cambia `nucleo/`, el pipeline ni ninguna métrica: es
  infraestructura, configuración y documentación.
- **Decisión de encuadre (importante para la defensa):** el despliegue
  gratuito (Hugging Face Spaces + PostgreSQL gestionado en Neon) es un
  **espejo de demostración**, no el despliegue objetivo. El objetivo sigue
  siendo un servidor nacional sin dependencias de nube extranjera
  (`docs/PROYECTO.md` §1, `docs/ARQUITECTURA.md` §6). Lo que sí se preserva en
  ambos casos: solo software libre, modelos abiertos y **clasificación sin
  salida a internet** (los modelos van horneados en la imagen, porque
  `RepresentadorSemantico.cargar()` fuerza `HF_HUB_OFFLINE=1`).
- **Qué NO se despliega:** el corpus crudo y el gold standard se quedan en la
  máquina local — `.dockerignore` replica las exclusiones del `.gitignore`. El
  sistema arranca con `datos/ejemplos/opiniones_ejemplo.csv` (4 opiniones) y
  se alimenta subiendo archivos desde el navegador. Es una decisión de
  privacidad, no de comodidad: las opiniones están anonimizadas por HMAC, pero
  el texto libre puede contener PII escrita por el propio autor.
- **Cambios en configuración** (`webapp/config/settings.py`, todos aditivos y
  con el comportamiento local intacto):
  - `DATABASE_URL` opcional, traducida por el nuevo `webapp/config/bd.py`; si
    no está, siguen mandando las variables `DB_*` de siempre. El traductor
    **exige TLS** (`sslmode=require`) cuando el host no es local y la URL no
    dice otra cosa.
  - WhiteNoise para servir estáticos sin Nginx delante.
  - `DJANGO_DETRAS_DE_PROXY` activa `SECURE_PROXY_SSL_HEADER`, redirección a
    HTTPS y cookies seguras. HSTS queda deliberadamente apagado: en un dominio
    compartido (`*.hf.space`) la cabecera afectaría a sitios de terceros.
    `manage.py check --deploy` pasa sin avisos salvo ese HSTS consciente.
- **Arranque idempotente** (`entrypoint.sh` + dos comandos de gestión nuevos):
  `migrate` → `asegurar_admin` (crea el usuario validador desde el entorno; no
  pisa una contraseña cambiada a mano) → `sembrar_demo` (siembra **solo si la
  base está vacía**, pasando el corpus por el mismo pipeline de fases 2-4 que
  la subida manual, y dejándolo todo en estado `propuesto` — el despliegue no
  simula validaciones humanas que no ocurrieron) → gunicorn con
  `--timeout 300`, porque la primera clasificación carga spaCy y los
  embeddings en memoria.
- **Pruebas nuevas:** `tests/test_despliegue.py` (13 casos) cubre el traductor
  de `DATABASE_URL` (incluido el TLS obligatorio en host remoto y las claves
  con caracteres codificados), la idempotencia de `asegurar_admin` y que
  `sembrar_demo` no duplique el corpus en cada reinicio. Suite completa:
  **113 en verde**.
- **CI arreglada (fallaba desde su primer push):** el workflow cacheaba
  `~/.cache/huggingface` pero nunca descargaba el modelo de embeddings, y
  `cargar()` fuerza el modo sin conexión — en un runner limpio las dos pruebas
  `modelo_real` no podían pasar. Se añadió el paso de descarga previa. De paso:
  Python **3.14** (la versión con la que se congeló `requirements-lock.txt` y
  se obtuvieron las métricas; el workflow decía 3.12) y torch en variante CPU,
  para no traer ~2 GB de ruedas CUDA inútiles en un runner sin GPU.
- **Inconsistencia detectada, sin resolver:** `CLAUDE.md` fija Python 3.12 como
  stack, pero el entorno real de trabajo —y el que produjo las métricas— es
  **3.14**. El `Dockerfile` y la CI siguen al entorno real, no al documento. Hay
  que decidir cuál es la versión oficial de la tesis y corregir el otro lado.
- **Pendiente:** (1) construir y probar la imagen (no hay Docker en la máquina
  de desarrollo, el `Dockerfile` está escrito pero sin ejecutar ni una vez);
  (2) compilar Tailwind en local — hoy entra por CDN y la interfaz necesita
  internet aunque el método no; (3) siguen abiertos los pendientes previos
  (`files (1).zip`, roles de usuario).

---

## 2026-09-23 — El prototipo pasa a llamarse ECO

- **Decisión:** el prototipo web se llama **ECO (Escucha Colectiva de Opiniones)**. Hasta
  hoy convivían tres nombres —`MIA_apklis-req-mining` en el repositorio, `mia` como
  paquete y "Requisitos desde Apklis" en la interfaz— y el Space de despliegue obliga a
  fijar uno antes de publicar, porque queda en la URL.
- **Por qué no seguir con MIA:** "MIA" son también las siglas de *Maestría en Informática
  Avanzada*, el propio grado de esta tesis; el documento acabaría diciendo "la tesis de MIA
  presenta a MIA". Además MIA nombraba al **método**, no a la aplicación.
- **Distinción que hay que mantener en el documento:** "el método" son las 5 fases (la
  contribución científica); **ECO** es el prototipo que lo implementa y lo demuestra. No son
  sinónimos. Anotado también en `docs/GLOSARIO.md` y en `CLAUDE.md`.
- **Qué cambió:** interfaz (título, encabezado de impresión y logotipo), `pyproject.toml`
  (`name = "eco"`), User-Agent del cliente de Apklis (`ECO-tesis-UCI/0.1`, así se identifica
  ante la tienda), nombres por defecto de base de datos y usuario (`eco_db`/`eco_user`) en
  settings, `.env.example` y CI, y el README (que además es la portada del Space).
- **Qué NO cambió, a propósito:**
  - `MIA_SAL_ANONIMIZACION` y la sal por defecto `mia-tesis-uci-sal-no-reversible`:
    cambiarlas alteraría **todos** los hashes de autor y rompería la continuidad con el
    corpus ya extraído. El nombre histórico queda documentado en el propio módulo.
  - La paleta Tailwind `apklis-*`: son los colores de marca de Apklis, no del prototipo.
  - La carpeta local de trabajo y las entradas antiguas de esta bitácora: son historia, no
    se reescriben.
- **Verificación:** 113 pruebas en verde tras reinstalar el paquete con el nombre nuevo.
- **Pendiente para la autora:** renombrar el repositorio en GitHub y actualizar el remoto.
- **Identidad visual (mismo día):** el isotipo cuenta el método completo, de fuera hacia
  dentro: el eco de la multitud (arcos), la opinión cruda (globo de diálogo), los requisitos
  ya separados por tipo (tres renglones de distinto peso — RF, RNF, Ruido) y el sello con el
  tic de la validación humana, que es la fase que nunca se omite. El logotipo repite la idea:
  la C y la O son los mismos arcos del eco.
  Se descartaron dos versiones anteriores: unas ondas radiando a un solo lado (se leía como
  un icono de wifi genérico) y un globo con eco pero sin contenido — ambas decían "escuchar",
  cuando lo que hace el sistema es **convertir opiniones ruidosas en requisitos clasificados
  que una persona valida**. Si la marca no dice eso, no dice nada del proyecto.
  Los archivos (SVG para la aplicación, PNG para el documento de tesis) **no se editan a
  mano**: los genera `scripts/marca.py`, que trae su propio rasterizador sin dependencias —
  la marca queda tan reproducible como los experimentos. Efecto secundario que hubo que
  resolver: al servir estáticos propios con manifiesto, `pytest` pasaba a depender de haber
  corrido `collectstatic`; `tests/conftest.py` lo aísla para que la suite siga siendo
  independiente del despliegue.
