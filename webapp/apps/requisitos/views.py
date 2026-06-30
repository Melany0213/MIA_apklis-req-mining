import csv

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView

from .models import CorridaEvaluacion

ETIQUETAS = ["RF", "RNF", "Ruido"]


class CorridaListaView(ListView):
    model = CorridaEvaluacion
    template_name = "evaluacion/lista.html"
    context_object_name = "corridas"
    ordering = ["-f1_global"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        corridas = ctx["corridas"]
        mejor_f1 = max((c.f1_global for c in corridas), default=0)
        mejor_tfidf = (
            CorridaEvaluacion.objects.filter(metodo="tfidf")
            .order_by("-f1_global")
            .first()
        )
        ctx["mejor_f1"] = mejor_f1
        ctx["mejor_tfidf_f1"] = mejor_tfidf.f1_global if mejor_tfidf else None
        ctx["etiquetas"] = ETIQUETAS
        return ctx


class CorridaDetalleView(DetailView):
    model = CorridaEvaluacion
    template_name = "evaluacion/detalle.html"
    context_object_name = "corrida"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        corrida = ctx["corrida"]

        # Lista lista para iterar en el template (evita acceso dinámico a dicts)
        ctx["metricas_lista"] = [
            {
                "etiqueta": etiqueta,
                **corrida.metricas_por_clase.get(etiqueta, {"precision": 0, "recall": 0, "f1": 0, "soporte": 0}),
            }
            for etiqueta in ETIQUETAS
        ]

        # Matriz con etiqueta de fila incluida
        ctx["matriz_filas"] = [
            {"etiqueta": ETIQUETAS[i], "valores": fila}
            for i, fila in enumerate(corrida.matriz_confusion)
        ] if corrida.matriz_confusion else []

        ctx["etiquetas"] = ETIQUETAS
        return ctx


def guardar_notas(request, pk):
    """Guarda las notas del investigador para una corrida."""
    corrida = get_object_or_404(CorridaEvaluacion, pk=pk)
    if request.method == "POST":
        corrida.notas = request.POST.get("notas", "")
        corrida.save(update_fields=["notas"])
    return redirect("evaluacion:detalle", pk=pk)


def exportar_csv(request):
    """Descarga todas las corridas en CSV para el documento de tesis."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="experimentos_mia.csv"'
    response.write("﻿")  # BOM para que Excel abra con tildes correctas

    writer = csv.writer(response)
    writer.writerow([
        "Fecha", "Representación", "Modelo embeddings", "Clasificador",
        "Hiperparámetros", "Semilla", "Corpus (n)", "Dataset",
        "Precisión global", "Recall global", "F1 global",
        "Precisión RF", "Recall RF", "F1 RF",
        "Precisión RNF", "Recall RNF", "F1 RNF",
        "Precisión Ruido", "Recall Ruido", "F1 Ruido",
        "Notas",
    ])

    for c in CorridaEvaluacion.objects.all():
        fila = [
            c.fecha.strftime("%Y-%m-%d %H:%M"),
            c.get_metodo_display(),
            c.modelo_embeddings,
            c.get_clasificador_display(),
            str(c.hiperparametros),
            c.semilla,
            c.tam_corpus,
            c.dataset,
            f"{c.precision_global:.4f}",
            f"{c.recall_global:.4f}",
            f"{c.f1_global:.4f}",
        ]
        for etiqueta in ETIQUETAS:
            m = c.metricas_por_clase.get(etiqueta, {})
            fila += [
                f"{m.get('precision', 0):.4f}",
                f"{m.get('recall', 0):.4f}",
                f"{m.get('f1', 0):.4f}",
            ]
        fila.append(c.notas)
        writer.writerow(fila)

    return response
