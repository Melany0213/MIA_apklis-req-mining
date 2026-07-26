from django.views.generic import ListView

from .models import Opinion


class OpinionListaView(ListView):
    """Corpus de opiniones (fase 1), de solo lectura."""

    model = Opinion
    template_name = "opiniones/lista.html"
    context_object_name = "opiniones"
    paginate_by = 25

    def get_queryset(self):
        return Opinion.objects.select_related("requisito").all()
