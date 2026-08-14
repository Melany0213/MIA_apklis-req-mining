from rest_framework import serializers

from .models import CorridaEvaluacion


class CorridaEvaluacionSerializer(serializers.ModelSerializer):
    """Serializa una corrida de evaluación registrada (comparación semántico vs. TF-IDF)."""

    class Meta:
        model = CorridaEvaluacion
        fields = [
            "id", "metodo", "modelo_embeddings", "clasificador", "hiperparametros",
            "semilla", "tam_corpus", "dataset", "precision_global", "recall_global",
            "f1_global", "metricas_por_clase", "matriz_confusion", "notas", "fecha",
        ]
        read_only_fields = fields

