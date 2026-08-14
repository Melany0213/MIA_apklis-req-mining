from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AbstractBaseUser
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import ListView
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ESTADOS, ETIQUETAS, Requisito
from .serializers import RequisitoSerializer


def _registrar_decision(
    requisito: Requisito,
    *,
    usuario: AbstractBaseUser,
    estado: str,
    notas: str,
    etiqueta_final: str = "",
) -> None:
    """Aplica la decisión del especialista sobre una propuesta (fase 5).

    Compartida por la vista web de validar/descartar y por la acción
    `validar` de `RequisitoViewSet`, para no duplicar la lógica de qué
    campos cambian cuando un humano decide sobre una propuesta.
    """
    requisito.etiqueta_final = etiqueta_final
    requisito.estado = estado
    requisito.validado_por = usuario
    requisito.fecha_validacion = timezone.now()
    requisito.notas = notas
    requisito.save()


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
        ctx["total_descartado"] = Requisito.objects.filter(estado="descartado").count()
        return ctx


@login_required
def validar(request, pk):
    """Muestra una opinión con su propuesta y registra la decisión del especialista."""
    requisito = get_object_or_404(Requisito.objects.select_related("opinion"), pk=pk)

    if request.method == "POST":
        etiqueta_final = request.POST.get("etiqueta_final")
        if etiqueta_final in dict(ETIQUETAS):
            _registrar_decision(
                requisito,
                usuario=request.user,
                estado="validado",
                notas=request.POST.get("notas", ""),
                etiqueta_final=etiqueta_final,
            )
        return redirect("validacion:cola")

    return render(
        request,
        "validacion/detalle.html",
        {"requisito": requisito, "etiquetas": ETIQUETAS},
    )


@login_required
def descartar(request, pk):
    """Descarta una opinión no aprovechable como requisito (spam, texto
    ininteligible, duplicado): sale de la cola de pendientes sin forzarla a
    ninguna de las 3 etiquetas finales (ver docstring de `Requisito`)."""
    requisito = get_object_or_404(Requisito.objects.select_related("opinion"), pk=pk)

    if request.method == "POST":
        _registrar_decision(
            requisito,
            usuario=request.user,
            estado="descartado",
            notas=request.POST.get("notas", ""),
        )

    return redirect("validacion:cola")


class RequisitoViewSet(viewsets.ReadOnlyModelViewSet):
    """`GET /api/requisitos/?estado=propuesto` — cola de validación para el
    especialista, con la acción `validar` para confirmar/corregir (fase 5).
    """

    queryset = Requisito.objects.select_related("opinion", "validado_por").all()
    serializer_class = RequisitoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def validar(self, request, pk=None):
        """`POST /api/requisitos/{id}/validar/` — igual que la vista web
        `validar`: exige sesión autenticada y una `etiqueta_final` válida."""
        requisito = self.get_object()
        etiqueta_final = request.data.get("etiqueta_final")
        if etiqueta_final not in dict(ETIQUETAS):
            return Response(
                {"detail": f"'etiqueta_final' debe ser una de {list(dict(ETIQUETAS))}."},
                status=400,
            )

        _registrar_decision(
            requisito,
            usuario=request.user,
            estado="validado",
            notas=request.data.get("notas", ""),
            etiqueta_final=etiqueta_final,
        )
        return Response(RequisitoSerializer(requisito).data)
