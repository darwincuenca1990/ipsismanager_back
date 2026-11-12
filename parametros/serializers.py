from rest_framework import serializers

from .models import Parametro


class ParametroSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parametro
        fields = ['id', 'nombre', 'valor', 'estado', 'fecha_registro']
        read_only_fields = ['id', 'fecha_registro']
