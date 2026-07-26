from django.contrib import admin

from .models import Opinion


@admin.register(Opinion)
class OpinionAdmin(admin.ModelAdmin):
    list_display = ("id", "texto_original", "aplicacion", "calificacion", "fecha_publicacion")
    search_fields = ("texto_original", "autor_anon")
    list_filter = ("aplicacion", "fuente")
