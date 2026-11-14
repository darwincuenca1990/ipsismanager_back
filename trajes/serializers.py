from rest_framework import serializers

from .models import AdquisicionTraje, ComposicionTraje, PrendaTraje, TipoTraje


class TipoTrajeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoTraje
        fields = '__all__'
        read_only_fields = ['id', 'fecha_registro', 'fecha_actualizacion']


class PrendaTrajeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrendaTraje
        fields = ['id', 'nombre_prenda', 'descripcion', 'fotografia', 'observaciones', 'estado']
        read_only_fields = ['id']


class ComposicionTrajeSerializer(serializers.ModelSerializer):
    prenda_detalle = PrendaTrajeSerializer(source='prenda', read_only=True)

    class Meta:
        model = ComposicionTraje
        fields = [
            'id', 'tipo_traje', 'prenda', 'prenda_detalle', 'cantidad_requerida',
            'precio_unitario', 'observaciones', 'estado',
        ]
        read_only_fields = ['id', 'prenda_detalle']


class AdquisicionTrajeSerializer(serializers.ModelSerializer):
    costo_total = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)

    class Meta:
        model = AdquisicionTraje
        fields = '__all__'
        read_only_fields = ['id', 'costo_total', 'fecha_registro']
