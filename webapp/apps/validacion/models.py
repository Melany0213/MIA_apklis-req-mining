from django.conf import settings
from django.db import models

from webapp.apps.opiniones.models import Opinion

ETIQUETAS = [
    ("RF", "Requisito Funcional"),
    ("RNF", "Requisito No Funcional"),
    ("Ruido", "Ruido"),
]

METODOS_PROPUESTA = [
    ("zero_shot", "Zero-shot (similitud a prototipos)"),
    ("semantico", "Semántico (Sentence-Transformers)"),
    ("tfidf", "TF-IDF (línea base)"),
]

ESTADOS = [
    ("propuesto", "Propuesto"),
    ("validado", "Validado"),
]


class Requisito(models.Model):
    """Propuesta de clasificación de una opinión y su validación humana (fase 5).

    La máquina propone `etiqueta_propuesta`; el especialista confirma o
    corrige en `etiqueta_final`. Mientras `estado == "propuesto"` la fila
    está en la cola de validación y `etiqueta_final` no cuenta como resultado
    aceptado (regla de oro del método, ver CLAUDE.md).
    """

    opinion = models.OneToOneField(Opinion, on_delete=models.CASCADE, related_name="requisito")
    etiqueta_propuesta = models.CharField("etiqueta propuesta", max_length=10, choices=ETIQUETAS)
    confianza = models.FloatField("confianza", null=True, blank=True)
    metodo = models.CharField(
        "método de la propuesta", max_length=20, choices=METODOS_PROPUESTA, default="zero_shot"
    )

    etiqueta_final = models.CharField(
        "etiqueta final", max_length=10, choices=ETIQUETAS, blank=True
    )
    estado = models.CharField("estado", max_length=20, choices=ESTADOS, default="propuesto")
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisitos_validados",
        verbose_name="validado por",
    )
    fecha_validacion = models.DateTimeField("fecha de validación", null=True, blank=True)
    notas = models.TextField("notas del especialista", blank=True)

    class Meta:
        verbose_name = "requisito"
        verbose_name_plural = "requisitos"
        ordering = ["estado", "-confianza"]

    def __str__(self) -> str:
        return f"opinión #{self.opinion_id} → {self.etiqueta_propuesta} ({self.get_estado_display()})"
