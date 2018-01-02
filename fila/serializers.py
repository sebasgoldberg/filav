from .models import *
from rest_framework import serializers
from expander import ExpanderSerializerMixin

class FilaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fila
        fields = ('id', 'nome', )

class LocalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Local
        fields = ('id', 'nome', )


class TurnoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Turno
        fields = ('id', 'fila', 'estado')
