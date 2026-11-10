from rest_framework import serializers

from .models import PlantillaCumpleanos, TarjetaCumpleanos


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


class TarjetaCumpleanosSerializer(serializers.ModelSerializer):
    bailarin_nombre = serializers.SerializerMethodField()
    estado_generacion_display = serializers.CharField(
        source='get_estado_generacion_display',
        read_only=True
    )
    estado_display = serializers.CharField(
        source='get_estado_display',
        read_only=True
    )
    aprobado_por_username = serializers.CharField(
        source='aprobado_por.username',
        read_only=True,
        default=None
    )
    rechazado_por_username = serializers.CharField(
        source='rechazado_por.username',
        read_only=True,
        default=None
    )

    class Meta:
        model = TarjetaCumpleanos
        fields = [
            'id',
            'bailarin',
            'bailarin_nombre',
            'anio',
            'imagen',
            'mensaje_generado',
            'estado_generacion',
            'estado_generacion_display',
            'motivo_no_generacion',
            'fecha_generacion',
            'estado',
            'estado_display',
            'fecha_aprobacion',
            'aprobado_por',
            'aprobado_por_username',
            'fecha_rechazo',
            'rechazado_por',
            'rechazado_por_username',
            'motivo_rechazo',
            'observaciones',
        ]
        read_only_fields = fields

    def get_bailarin_nombre(self, tarjeta):
        return f'{tarjeta.bailarin.nombres} {tarjeta.bailarin.apellidos}'


class RechazoTarjetaSerializer(serializers.Serializer):
    motivo = serializers.CharField()

    def validate_motivo(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                'El motivo del rechazo es obligatorio.'
            )
        return value
