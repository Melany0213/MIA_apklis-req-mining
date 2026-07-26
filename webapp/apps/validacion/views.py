from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import ListView

from .models import ESTADOS, ETIQUETAS, Requisito


class ColaValidacionView(ListView):
    """Cola de propuestas pendientes de validación humana (fase 5)."""

    model = Requisito
    template_name = "validacion/cola.html"
    context_object_name = "requisitos"
    paginate_by = 20

    def get_queryset(self):
        estado = self.request.GET.get("estado", "propuesto")
        return (
            Requisito.objects.select_related("opinion", "validado_por")
            .filter(estado=estado)
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["estado_actual"] = self.request.GET.get("estado", "propuesto")
        ctx["estados"] = ESTADOS
        ctx["total_propuesto"] = Requisito.objects.filter(estado="propuesto").count()
        ctx["total_validado"] = Requisito.objects.filter(estado="validado").count()
        return ctx


@login_required
def validar(request, pk):
    """Muestra una opinión con su propuesta y registra la decisión del especialista."""
    requisito = get_object_or_404(Requisito.objects.select_related("opinion"), pk=pk)

    if request.method == "POST":
        etiqueta_final = request.POST.get("etiqueta_final")
        if etiqueta_final in dict(ETIQUETAS):
            requisito.etiqueta_final = etiqueta_final
            requisito.estado = "validado"
            requisito.validado_por = request.user
            requisito.fecha_validacion = timezone.now()
            requisito.notas = request.POST.get("notas", "")
            requisito.save()
        return redirect("validacion:cola")

    return render(
        request,
        "validacion/detalle.html",
        {"requisito": requisito, "etiquetas": ETIQUETAS},
    )
