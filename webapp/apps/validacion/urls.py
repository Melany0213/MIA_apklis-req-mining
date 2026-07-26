from django.urls import path

from . import views

app_name = "validacion"

urlpatterns = [
    path("", views.ColaValidacionView.as_view(), name="cola"),
    path("<int:pk>/", views.validar, name="validar"),
]
