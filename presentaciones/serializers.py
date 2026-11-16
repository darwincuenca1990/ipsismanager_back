from django.db import transaction
from rest_framework import serializers

from bailarines.models import Bailarin
from coreografias.models import Coreografia

from .models import Bitacora, Presentacion, PresentacionElenco


class BitacoraSerializer(serializers.Serializer):
    bailarin = serializers.PrimaryKeyRelatedField(queryset=Bailarin.objects.all())
    coreografias = serializers.PrimaryKeyRelatedField(
        queryset=Coreografia.objects.all(), many=True, allow_empty=True
    )

    def validate(self, attrs):
        faltantes = {
            field: 'Este campo es obligatorio.'
            for field in ('bailarin', 'coreografias') if field not in attrs
        }
        if faltantes:
            raise serializers.ValidationError(faltantes)
        return attrs

    def validate_coreografias(self, coreografias):
        if len({coreografia.pk for coreografia in coreografias}) != len(coreografias):
            raise serializers.ValidationError('No se permiten coreografías duplicadas.')
        return coreografias


class ElencosField(serializers.ListField):
    def to_representation(self, data):
        return super().to_representation([item.elenco for item in data.all()])


class PresentacionSerializer(serializers.ModelSerializer):
    elencos = ElencosField(
        child=serializers.ChoiceField(choices=Bailarin.Elenco.choices),
        allow_empty=False
    )
    bitacora = BitacoraSerializer(many=True, required=False)
    costo_neto = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Presentacion
        fields = [
            'id', 'fecha', 'lugar', 'hora_presentacion', 'persona_cargo',
            'costo_total_presentacion', 'costo_transporte', 'costo_neto',
            'nombre_transporte', 'tipo_presentacion', 'elencos', 'bitacora',
        ]
        read_only_fields = ['id', 'costo_neto']

    def validate_elencos(self, elencos):
        if len(set(elencos)) != len(elencos):
            raise serializers.ValidationError('No se permiten elencos duplicados.')
        return elencos

    def validate_bitacora(self, bitacora):
        bailarines = [item['bailarin'].pk for item in bitacora]
        if len(set(bailarines)) != len(bailarines):
            raise serializers.ValidationError('No se permiten bailarines duplicados.')
        return bitacora

    def validate(self, attrs):
        tipo = attrs.get(
            'tipo_presentacion',
            self.instance.tipo_presentacion if self.instance else None
        )
        elencos = attrs.get('elencos')
        if elencos is None and self.instance:
            elencos = list(self.instance.elencos.values_list('elenco', flat=True))
        if tipo == Presentacion.Tipo.UN_ELENCO and elencos and len(elencos) != 1:
            raise serializers.ValidationError({
                'elencos': 'Una presentación de tipo UN ELENCO debe tener un solo elenco.'
            })
        return attrs

    @staticmethod
    def guardar_relaciones(instance, elencos=None, bitacora=None):
        if elencos is not None:
            instance.elencos.all().delete()
            PresentacionElenco.objects.bulk_create([
                PresentacionElenco(presentacion=instance, elenco=elenco)
                for elenco in elencos
            ])
        if bitacora is not None:
            instance.bitacora.all().delete()
            for item in bitacora:
                detalle = Bitacora.objects.create(
                    presentacion=instance, bailarin=item['bailarin']
                )
                detalle.coreografias.set(item['coreografias'])

    @transaction.atomic
    def create(self, validated_data):
        elencos = validated_data.pop('elencos')
        bitacora = validated_data.pop('bitacora', [])
        instance = super().create(validated_data)
        self.guardar_relaciones(instance, elencos, bitacora)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        elencos = validated_data.pop('elencos', None)
        bitacora = validated_data.pop('bitacora', None)
        instance = super().update(instance, validated_data)
        self.guardar_relaciones(instance, elencos, bitacora)
        return instance
