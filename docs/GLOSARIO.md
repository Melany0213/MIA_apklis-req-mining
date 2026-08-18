# GLOSARIO.md — Términos del dominio

Usa siempre los términos canónicos. No introduzcas sinónimos en el código ni en la interfaz.

- **RF (Requisito Funcional):** algo que la aplicación debe hacer (p. ej., "permitir subir varias
  fotos a la vez").
- **RNF (Requisito No Funcional):** atributo de calidad sobre *cómo* se comporta la aplicación
  (rendimiento, estabilidad, usabilidad, seguridad, etc.). Ej.: "que no se cierre al subir fotos".
- **Ruido:** opinión sin información útil para extraer requisitos (p. ej., "muy buena app",
  cinco estrellas y nada más).
- **CrowdRE (Crowd-based Requirements Engineering):** ingeniería de requisitos basada en la
  multitud; usar la retroalimentación masiva de los usuarios como fuente de requisitos.
- **Opinión / reseña:** comentario de un usuario en la tienda de aplicaciones (entrada del método).
- **Embedding / representación semántica contextual:** vector que captura el significado de un
  texto; permite reconocer que frases distintas expresan lo mismo.
- **TF-IDF:** representación basada en frecuencia de palabras. Aquí es la **línea base** contra la
  que se compara el método semántico.
- **Gold standard:** subconjunto del corpus etiquetado manualmente, usado como referencia para
  medir el rendimiento.
- **Precisión / exhaustividad (recall) / F1:** métricas de evaluación de la clasificación.
- **Matriz de confusión:** tabla que muestra aciertos y errores por clase (RF, RNF, Ruido).
- **Apklis:** tienda nacional cubana de distribución de aplicaciones móviles (Proyecto Z17);
  fuente de datos y caso de estudio.
- **Soberanía tecnológica:** principio de depender de tecnología propia (software libre, modelos
  abiertos, despliegue local), no de plataformas extranjeras.
- **Validación humana (fase 5):** revisión del especialista que confirma o corrige la propuesta del
  clasificador antes de aceptarla. Obligatoria.

## Criterios operativos de validación (fase 5)

Derivados de la sesión de validación del 2026-08-14 sobre el lote importado
(498 opiniones). No son reglas cerradas ni sustituyen el criterio del
especialista caso a caso — son la base para decidir de forma consistente
ante patrones que se repiten mucho en el corpus. Pendiente de refinar junto
con el diccionario DNJL (`nucleo/preprocesamiento/dnjl.py`) más adelante.

- **Elogio genérico sin atributo de calidad ni pedido concreto → Ruido.**
  Ej.: "buena", "excelente", "me encanta", "5 estrellas". Es el caso más
  frecuente del corpus (con diferencia).
- **Palabra de atributo de calidad presente (eficaz, eficiente, rápido/a,
  estable, segura, resiliente...) → candidato a RNF**, incluso en tono de
  elogio: reconoce una cualidad específica, no alaba en general.
- **Queja de lentitud/demora:** si el usuario atribuye la causa explícitamente
  a la red/conexión/operador (p. ej. ETECSA) → Ruido (fuera del control del
  sistema); si no atribuye una causa externa → RNF (rendimiento).
- **Pedido de más aplicaciones/contenido en el catálogo → Ruido.** No es una
  función del software en sí (depende de que terceros suban sus apps), a
  diferencia de un RF sobre una función que sí puede construirse. Criterio
  adoptado por decisión explícita de la especialista, discutible y a
  revisar si el patrón se vuelve muy frecuente.
- **Fallo funcional concreto y específico → RF.** Ej.: "no actualiza", "no
  reconoce el pago", "no se puede instalar la apk". Aunque el texto sea
  corto, si nombra una acción del sistema que falla, es señal real.
- **Queja de usabilidad concreta (no solo "es difícil") → RNF.** Ej.: "da
  mucho trabajo instalarla".
- **Texto vago o pregunta sin especificar qué se pide → Ruido**, aunque
  sugiera confusión de uso. Sin un dato concreto (qué pantalla, qué acción),
  no hay información accionable para un requisito.
- **Texto sin sentido, dato personal incidental (teléfono, etc.) o contenido
  no relacionado con la app → descartar, no Ruido.** Ruido es una opinión
  evaluada que no aporta contenido de requisito; descartar es para opiniones
  que ni siquiera son aprovechables como opinión.
