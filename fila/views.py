from django.shortcuts import render

from .models import Fila
from .serializers import *
from rest_framework import viewsets

class FilaViewSet(viewsets.ModelViewSet):
    queryset = Fila.objects.all()
    serializer_class = FilaSerializer


class TurnoViewSet(viewsets.ModelViewSet):
    queryset = Turno.objects.all()
    serializer_class = TurnoSerializer

class ClienteTurnosAtivosViewSet(TurnoViewSet):
    queryset = Turno.ativos.all()
    def get_queryset(self):
        qs = super(ClienteTurnosAtivosViewSet, self).get_queryset()
        qs = qs.filter(cliente=self.request.user)
        return qs
