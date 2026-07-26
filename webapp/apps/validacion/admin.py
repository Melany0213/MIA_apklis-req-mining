from django.contrib import admin

from .models import Requisito


@admin.register(Requisito)
class RequisitoAdmin(admin.ModelAdmin):
    list_display = ("id", "opinion", "etiqueta_propuesta", "etiqueta_final", "estado", "validado_por")
    list_filter = ("estado", "etiqueta_propuesta", "etiqueta_final", "metodo")
    search_fields = ("opinion__texto_original",)
