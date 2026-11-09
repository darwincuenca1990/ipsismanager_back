from rest_framework import serializers

from .models import PlantillaCumpleanos


class PlantillaCumpleanosSerializer(serializers.ModelSerializer):
    elenco_display = serializers.CharField(
        source='get_elenco_display',
        read_only=True
    )

    class Meta:
        model = PlantillaCumpleanos
        fields = [
            'id',
            'elenco',
            'elenco_display',
            'mensaje',
            'activa',
        ]
        read_only_fields = ['id']
