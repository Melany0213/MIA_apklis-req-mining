from rest_framework import serializers

from webapp.apps.opiniones.serializers import OpinionSerializer

from .models import Requisito


class RequisitoSerializer(serializers.ModelSerializer):
    """Serializa una propuesta + su validación humana (fase 5), de solo lectura.

    `POST /api/requisitos/{id}/validar/` (acción de `RequisitoViewSet`) es la
    única forma de modificar un `Requisito` vía API — no hay update/create
    genérico, para no abrir una vía que evite el paso de validación.
    """

    opinion = OpinionSerializer(read_only=True)

    class Meta:
        model = Requisito
        fields = [
            "id", "opinion", "etiqueta_propuesta", "confianza", "metodo",
            "etiqueta_final", "estado", "validado_por", "fecha_validacion", "notas",
        ]
        read_only_fields = fields

