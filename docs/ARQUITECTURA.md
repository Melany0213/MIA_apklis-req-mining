# ARQUITECTURA.md — Arquitectura, datos y hoja de ruta

Referencia técnica para Claude Code. Propuesta inicial; ajústala con la autora antes de
consolidar decisiones grandes.

## 1. Principio rector

El **método** (paquete `nucleo/`) es independiente de la web. Debe poder ejecutarse y probarse
desde un script o un notebook, sin Django. La **webapp** consume al `nucleo/` como una librería.
Esto protege la contribución científica y facilita las pruebas y los experimentos.

```
opiniones ──► [nucleo: extracción → preprocesamiento → representación → clasificación] ──► propuestas
                                                                                           │
                                                                          webapp (validación humana)
                                                                                           ▼
                                                                                  requisitos validados
```

## 2. Estructura de carpetas propuesta

```
requisitos-apklis/
├── CLAUDE.md
├── README.md
├── pyproject.toml            # o requirements.txt (versiones ancladas)
├── .env.example              # variables de entorno (sin secretos reales)
├── .gitignore                # ignora datos/ sensibles, modelos descargados, .env
│
├── nucleo/                   # EL MÉTODO (sin dependencias de Django)
│   ├── extraccion/           # cliente/scraper de Apklis → corpus
│   ├── preprocesamiento/     # spaCy es-CU: limpieza, normalización, lematización
│   ├── representacion/
│   │   ├── semantica.py      # embeddings (Sentence-Transformers/Transformers)
│   │   └── tfidf.py          # línea base
│   ├── clasificacion/        # modelos sklearn (entrenar, predecir, persistir)
│   ├── evaluacion/           # métricas precision/recall/F1, matriz de confusión, comparación
│   └── pipeline.py           # orquesta fases 1–4 sobre un corpus
│
├── webapp/                   # Django + DRF
│   ├── manage.py
│   ├── config/               # settings, urls, wsgi/asgi
│   └── apps/
│       ├── usuarios/         # auth + roles (admin, especialista, analista)
│       ├── opiniones/        # corpus, importación, consulta
│       ├── requisitos/       # propuestas y requisitos clasificados
│       └── validacion/       # interfaz de revisión humana (fase 5)
│
├── datos/                    # corpus crudo, gold standard (NO versionar lo sensible)
├── modelos/                  # modelos entrenados / descargados (NO versionar; .gitignore)
├── notebooks/                # exploración y experimentos
├── tests/                    # pytest (espejo de nucleo/ y webapp/)
└── docs/                     # PROYECTO.md, ARQUITECTURA.md, GLOSARIO.md, bitacora-experimentos.md
```

## 3. Modelo de datos (entidades principales)

Diseño orientativo para los modelos de Django. Las etiquetas canónicas son `RF`, `RNF`, `Ruido`.

- **Aplicacion** — `nombre`, `paquete`, `version`, `descargas`, `descripcion`.
- **Opinion** — `texto`, `fecha`, `calificacion` (nullable), `idioma`, `autor_anon` (hash/anónimo),
  `aplicacion` (FK). El texto original se conserva; el preprocesado puede derivarse o cachearse.
- **Clasificacion** — `opinion` (FK), `etiqueta` (`RF`/`RNF`/`Ruido`), `confianza` (float),
  `metodo` (`semantico`/`tfidf`), `modelo_version`, `fecha`.
- **Requisito** — `opinion` (FK), `tipo` (`RF`/`RNF`), `atributo_calidad` (para RNF: rendimiento,
  estabilidad, usabilidad, seguridad…), `texto_normalizado`,
  `estado` (`propuesto`/`validado`/`descartado`), `validado_por` (FK Usuario, nullable),
  `fecha_validacion`.
- **Usuario** — auth de Django + `rol` (`administrador`/`especialista`/`analista`).
- **EtiquetaManual** (gold standard) — `opinion` (FK), `etiqueta_referencia`, `etiquetado_por`.
- **CorridaEvaluacion** — `metodo`, `dataset`, `precision`, `recall`, `f1`, `fecha`, `notas`
  (para registrar y comparar experimentos de forma reproducible).

## 4. API (DRF) — endpoints orientativos

- `GET /api/opiniones/` — listar/filtrar opiniones del corpus.
- `POST /api/clasificar/` — clasificar un lote de opiniones (devuelve propuestas, no las da por válidas).
- `GET /api/requisitos/?estado=propuesto` — cola de validación para el especialista.
- `POST /api/requisitos/{id}/validar/` — confirmar/corregir (fase 5).
- `GET /api/evaluacion/` — métricas de las corridas (comparación semántico vs TF-IDF).

## 5. Hoja de ruta sugerida (incremental)

Trabajar una etapa a la vez, con pruebas, y registrar resultados en la bitácora.

1. **Andamiaje:** repo, `pyproject`/requirements con versiones ancladas, estructura de carpetas,
   `nucleo/` vacío con pruebas, proyecto Django mínimo, PostgreSQL conectado.
2. **Fase 1 – Extracción:** obtener y almacenar un corpus de Apklis (con anonimización).

   Apklis expone una API REST pública y sin autenticación en `https://api.apklis.cu/`
   (la misma que consume su sitio Angular en `https://www.apklis.cu`). Endpoints usados:
   - `GET /v2/application/` — catálogo de apps (paginado `limit`/`offset`; 1481 apps a jul-2026).
   - `GET /v2/review/?application=<package_name>&public=true` — reseñas públicas de una app
     (`comment`, `rating`, `published`, `version`, `user.username`).
   No hace falta scraping de HTML. `nucleo/extraccion/apklis.py` implementa un cliente
   respetuoso (espera entre peticiones, User-Agent identificable) y
   `nucleo/extraccion/anonimizacion.py` hashea `user.username` con HMAC-SHA256 antes de que
   el dato toque disco — nunca se guarda username, nombre real ni avatar.
   Caveat: el texto libre del comentario puede contener PII que el propio autor escribió
   (teléfonos, nombres) — no se filtra en la extracción; a decidir si se redacta en fase 2.
3. **Fase 2 – Preprocesamiento:** canal spaCy es-CU + pruebas con ejemplos de jerga local.
4. **Fase 3 – Representación:** embeddings semánticos **y** baseline TF-IDF.
5. **Fase 4 – Clasificación:** entrenar/evaluar clasificadores sobre ambas representaciones.
6. **Evaluación:** gold standard, métricas y comparación reproducibles (matriz de confusión).
7. **Webapp:** modelos, importación de opiniones, **interfaz de validación humana**, panel de métricas.
8. **Cierre:** scripts de reproducción, documentación y empaquetado para despliegue local.

## 6. Notas de despliegue

- Pensar el despliegue para **servidores locales/nacionales**, sin dependencias de nube de pago.
- Descargar los modelos de PLN una sola vez y operar **sin conexión** después.
- Variables sensibles por entorno; `.env` fuera del control de versiones.
