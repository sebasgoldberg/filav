from .models import Fila
from rest_framework import serializers

# Serializers define the API representation.
class FilaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fila
        fields = ('id', 'nome', )
