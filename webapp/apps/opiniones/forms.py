from django import forms

from .pipeline import EXTENSIONES_PERMITIDAS


class SubidaOpinionesForm(forms.Form):
    """Formulario de subida manual de opiniones (.csv o .json) para el pipeline."""

    archivo = forms.FileField(label="Archivo de opiniones (.csv o .json)")

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        extension = archivo.name.rsplit(".", 1)[-1].lower() if "." in archivo.name else ""
        if extension not in EXTENSIONES_PERMITIDAS:
            raise forms.ValidationError("El archivo debe tener extensión .csv o .json.")
        return archivo
