from django.shortcuts import render

from .models import Fila
from .serializers import *
from rest_framework import viewsets

class FilaViewSet(viewsets.ModelViewSet):
    queryset = Fila.objects.all()
    serializer_class = FilaSerializer

class LocalViewSet(viewsets.ModelViewSet):
    queryset = Local.objects.all()
    serializer_class = LocalSerializer


class TurnoViewSet(viewsets.ModelViewSet):
    queryset = Turno.objects.all()
    serializer_class = TurnoSerializer

class ClienteTurnosAtivosViewSet(TurnoViewSet):
    queryset = Turno.ativos.all()
    def get_queryset(self):
        qs = super(ClienteTurnosAtivosViewSet, self).get_queryset()
        qs = qs.filter(cliente=self.request.user)
        return qs

from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class ClienteView(LoginRequiredMixin, TemplateView):

    template_name = "fila/cliente/index.html"


from django.contrib.auth.mixins import PermissionRequiredMixin

class ScannerView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):

    template_name = "fila/scanner/index.html"
    permission_required = ('fila.habilitar_scanner',)


class PostoView(LoginRequiredMixin, TemplateView):

    template_name = "fila/posto/index.html"


