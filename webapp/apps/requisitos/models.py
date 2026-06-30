from django.db import models

METODOS = [
    ("semantico", "Semántico (Sentence-Transformers)"),
    ("tfidf", "TF-IDF (línea base)"),
]

CLASIFICADORES = [
    ("svm", "SVM"),
    ("logreg", "Regresión Logística"),
    ("random_forest", "Random Forest"),
    ("naive_bayes", "Naive Bayes"),
    ("knn", "K-Nearest Neighbors"),
]


class CorridaEvaluacion(models.Model):
    """Registro de una corrida de evaluación del clasificador (experimento reproducible)."""

    metodo = models.CharField("representación", max_length=20, choices=METODOS)
    modelo_embeddings = models.CharField(
        "modelo de embeddings", max_length=200, blank=True,
        help_text="Solo aplica para método semántico.",
    )
    clasificador = models.CharField("clasificador", max_length=30, choices=CLASIFICADORES)
    hiperparametros = models.JSONField("hiperparámetros", default=dict)
    semilla = models.IntegerField("semilla aleatoria", default=42)
    tam_corpus = models.IntegerField("tamaño del corpus", default=0)
    dataset = models.CharField("nombre del dataset", max_length=200, blank=True)

    precision_global = models.FloatField("precisión global")
    recall_global = models.FloatField("recall global")
    f1_global = models.FloatField("F1 global")
    metricas_por_clase = models.JSONField("métricas por clase", default=dict)
    matriz_confusion = models.JSONField("matriz de confusión", default=list)

    notas = models.TextField("notas del investigador", blank=True)
    fecha = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        ordering = ["-f1_global"]
        verbose_name = "corrida de evaluación"
        verbose_name_plural = "corridas de evaluación"

    def __str__(self) -> str:
        return f"{self.get_metodo_display()} + {self.get_clasificador_display()} | F1={self.f1_global:.3f}"

    @property
    def f1_pct(self) -> str:
        return f"{self.f1_global * 100:.1f}%"

    @property
    def es_mejor_que_baseline(self) -> bool | None:
        """True si es semántico y supera al mejor TF-IDF registrado."""
        if self.metodo != "semantico":
            return None
        mejor_tfidf = CorridaEvaluacion.objects.filter(metodo="tfidf").order_by("-f1_global").first()
        if mejor_tfidf is None:
            return None
        return self.f1_global > mejor_tfidf.f1_global
