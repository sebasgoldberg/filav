from django.shortcuts import render

from .models import Fila
from .serializers import FilaSerializer
from rest_framework import viewsets

# ViewSets define the view behavior.
class FilaViewSet(viewsets.ModelViewSet):
    queryset = Fila.objects.all()
    serializer_class = FilaSerializer
