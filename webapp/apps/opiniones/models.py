from django.db import models


class Opinion(models.Model):
    """Opinión cruda extraída de la tienda de aplicaciones (fase 1 del método)."""

    texto_original = models.TextField("texto original")
    texto_normalizado = models.TextField("texto normalizado", blank=True)
    fecha_publicacion = models.DateTimeField("fecha de publicación", null=True, blank=True)
    calificacion = models.IntegerField("calificación", null=True, blank=True)
    aplicacion = models.CharField("aplicación", max_length=200, blank=True)
    autor_anon = models.CharField("autor anónimo", max_length=64, blank=True)
    fuente = models.CharField("fuente", max_length=50, blank=True)
    creado = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "opinión"
        verbose_name_plural = "opiniones"
        ordering = ["-fecha_publicacion"]

    def __str__(self) -> str:
        return self.texto_original[:60]
