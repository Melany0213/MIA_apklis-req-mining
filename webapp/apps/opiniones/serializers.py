from rest_framework import serializers

from .models import Opinion


class OpinionSerializer(serializers.ModelSerializer):
    """Serializa el corpus de opiniones (fase 1), de solo lectura."""

    class Meta:
        model = Opinion
        fields = [
            "id", "texto_original", "texto_normalizado", "fecha_publicacion",
            "calificacion", "aplicacion", "autor_anon", "fuente", "creado",
        ]
        read_only_fields = fields


class PropuestaSerializer(serializers.Serializer):
    """Serializa una `nucleo.pipeline.Propuesta`: propuesta sin validar, no
    ligada a ningún modelo de Django (no se persiste)."""

    texto_original = serializers.CharField()
    texto_preprocesado = serializers.CharField()
    etiqueta = serializers.CharField()
    confianza = serializers.FloatField()
    metodo = serializers.CharField()

