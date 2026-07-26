from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.generic import ListView

from nucleo.scripts.exportar_propuestas import generar_propuestas
from nucleo.scripts.importar_opiniones import importar_a_bd

from .forms import SubidaOpinionesForm
from .models import Opinion
from .pipeline import ArchivoOpinionesInvalido, leer_corpus, obtener_componentes


class OpinionListaView(ListView):
    """Corpus de opiniones (fase 1), de solo lectura."""

    model = Opinion
    template_name = "opiniones/lista.html"
    context_object_name = "opiniones"
    paginate_by = 25

    def get_queryset(self):
        return Opinion.objects.select_related("requisito").all()


@login_required
def subir(request):
    """Sube un CSV/JSON de opiniones y lo pasa por el mismo pipeline que la consola.

    Preprocesamiento → DNJL → lematización → representación semántica →
    clasificador zero-shot (idéntico a `exportar_propuestas` +
    `importar_opiniones`). Las opiniones resultantes quedan con
    `estado="propuesto"`, en la misma cola de `/validacion/`.
    """
    if request.method == "POST":
        form = SubidaOpinionesForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                corpus = leer_corpus(form.cleaned_data["archivo"])
                componentes = obtener_componentes()
                propuestas = generar_propuestas(
                    corpus, componentes.lematizador, componentes.clasificador
                )
                creadas_opinion, creadas_requisito = importar_a_bd(corpus, propuestas)
            except ArchivoOpinionesInvalido as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request,
                    f"{creadas_opinion} opiniones nuevas importadas "
                    f"({creadas_requisito} en la cola de validación).",
                )
                return redirect("opiniones:lista")
    else:
        form = SubidaOpinionesForm()

    return render(request, "opiniones/subir.html", {"form": form})
