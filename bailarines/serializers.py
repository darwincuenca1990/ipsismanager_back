
from django.db import transaction
from rest_framework import serializers

from .models import Bailarin, GrupoFamiliar, Inscripcion


class BailarinInscripcionSerializer(serializers.ModelSerializer):

    estado = serializers.ChoiceField(
        choices=Inscripcion.Estado.choices,
        required=True
    )

    class Meta:
        model = Inscripcion
        fields = [
            'fecha_ingreso_agrupacion',
            'estado',
            'motivo_ingreso_agrupacion',
            'fecha_salida',
        ]


class GrupoFamiliarSerializer(serializers.ModelSerializer):

    class Meta:
        model = GrupoFamiliar
        fields = [
            'id',
            'apellidos_papa',
            'nombres_papa',
            'celular_papa',
            'lugar_trabajo_papa',
            'apellidos_mama',
            'nombres_mama',
            'celular_mama',
            'lugar_trabajo_mama',
            'nombres_completos_representante',
            'lugar_trabajo_representante',
            'celular_representante',
            'parentesco',
        ]
        read_only_fields = ['id']



class BailarinSerializer(serializers.ModelSerializer):

    grupo_familiar = GrupoFamiliarSerializer(read_only=True)

    inscripcion = BailarinInscripcionSerializer(
        required=False,
        write_only=True
    )

    grupo_familiar_id = serializers.PrimaryKeyRelatedField(
        queryset=GrupoFamiliar.objects.all(),
        source='grupo_familiar',
        write_only=True
    )

    class Meta:
        model = Bailarin
        fields = [
            'id',
            'grupo_familiar',
            'grupo_familiar_id',
            'inscripcion',
            'elenco',
            'cedula',
            'apellidos',
            'nombres',
            'estudia',
            'institucion_estudio',
            'trabaja',
            'lugar_trabajo',
            'direccion_domicilio',
            'referencia_domicilio',
            'vive_con',
            'fecha_nacimiento',
            'lugar_nacimiento',
            'celular',
            'padece_enfermedad',
            'detalle_enfermedad',
            'correo',
            'fotografia',
            'autorizado_publicacion',
            'fecha_autorizacion_publicacion',
        ]

        read_only_fields = ['id']

    def validate(self, attrs):
        if self.instance is None and 'inscripcion' not in attrs:
            raise serializers.ValidationError({
                'inscripcion': 'Este campo es obligatorio al crear un bailarín.'
            })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        inscripcion_data = validated_data.pop('inscripcion')
        bailarin = super().create(validated_data)
        Inscripcion.objects.create(
            bailarin=bailarin,
            **inscripcion_data
        )
        return bailarin

    @transaction.atomic
    def update(self, instance, validated_data):
        inscripcion_data = validated_data.pop('inscripcion', None)
        bailarin = super().update(instance, validated_data)

        if inscripcion_data is not None:
            inscripcion = bailarin.inscripciones.order_by(
                '-fecha_ingreso_agrupacion',
                '-id'
            ).first()
            if inscripcion is None:
                Inscripcion.objects.create(
                    bailarin=bailarin,
                    **inscripcion_data
                )
            else:
                for field, value in inscripcion_data.items():
                    setattr(inscripcion, field, value)
                inscripcion.save()

        return bailarin



class InscripcionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Inscripcion
        fields = [
            'id',
            'bailarin',
            'fecha_ingreso_agrupacion',
            'estado',
            'motivo_ingreso_agrupacion',
            'fecha_salida',
        ]
        read_only_fields = ['id']
