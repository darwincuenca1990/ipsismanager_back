from rest_framework import serializers

from .models import PlantillaCumpleanos, PublicacionRedSocial, TarjetaCumpleanos


class PublicacionRedSocialSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicacionRedSocial
        fields = [
            'id', 'tarjeta', 'plataforma', 'estado', 'texto_publicacion',
            'fecha_publicacion', 'id_publicacion_externa', 'mensaje_error',
            'creado_en', 'actualizado_en',
        ]
        read_only_fields = fields


class FiltroPublicacionesSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(
        choices=PublicacionRedSocial.Estado.choices, required=False
    )
    mes_desde = serializers.CharField(required=False)
    mes_hasta = serializers.CharField(required=False)
    anio = serializers.IntegerField(min_value=1, max_value=9999, required=False)

    def to_internal_value(self, data):
        desconocidos = set(data.keys()) - set(self.fields)
        if desconocidos:
            raise serializers.ValidationError({
                campo: 'Parámetro no permitido.' for campo in sorted(desconocidos)
            })
        return super().to_internal_value(data)

    def _validar_mes(self, value):
        meses = (
            'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
            'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE',
            'DICIEMBRE',
        )
        valor = value.strip().upper()
        if valor in meses:
            return meses.index(valor) + 1
        if valor.isascii() and valor.isdigit() and 1 <= int(valor) <= 12:
            return int(valor)
        raise serializers.ValidationError(
            'Indique un mes válido, por nombre o número del 1 al 12.'
        )

    def validate_mes_desde(self, value):
        return self._validar_mes(value)

    def validate_mes_hasta(self, value):
        return self._validar_mes(value)

    def validate(self, attrs):
        desde = attrs.get('mes_desde')
        hasta = attrs.get('mes_hasta')
        if (desde is None) != (hasta is None):
            raise serializers.ValidationError({
                'mes_desde': 'Debe enviar ambos extremos del rango de meses.'
            })
        if desde is not None and desde > hasta:
            raise serializers.ValidationError({
                'mes_hasta': 'Debe ser igual o posterior a mes_desde.'
            })
        return attrs


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
