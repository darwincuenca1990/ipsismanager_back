
import json

from django.db import transaction
from rest_framework import serializers

from .google_drive import upload_bailarin_photo
from .models import Bailarin, GrupoFamiliar, Inscripcion


class CumpleanosSemanaParamsSerializer(serializers.Serializer):
    semana = serializers.ChoiceField(
        choices=['anterior', 'actual', 'siguiente'],
        default='actual'
    )


class CumpleanosMesParamsSerializer(serializers.Serializer):
    mes = serializers.CharField()

    def validate_mes(self, value):
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


class FotografiaField(serializers.ImageField):

    def to_representation(self, value):
        return value or None


class BailarinInscripcionSerializer(serializers.ModelSerializer):

    estado = serializers.ChoiceField(
        choices=Inscripcion.Estado.choices,
        required=True
    )

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as error:
                raise serializers.ValidationError(
                    'Debe ser un objeto JSON válido.'
                ) from error
        return super().to_internal_value(data)

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
    genero = serializers.ChoiceField(
        choices=Bailarin.Genero.choices,
        required=False,
        allow_null=True
    )

    fecha_ingreso_agrupacion = serializers.DateField(
        source='inscripcion_fecha_ingreso_agrupacion',
        read_only=True,
        allow_null=True
    )
    estado = serializers.CharField(
        source='inscripcion_estado',
        read_only=True,
        allow_null=True
    )
    motivo_ingreso_agrupacion = serializers.CharField(
        source='inscripcion_motivo_ingreso_agrupacion',
        read_only=True,
        allow_null=True
    )
    fecha_salida = serializers.DateField(
        source='inscripcion_fecha_salida',
        read_only=True,
        allow_null=True
    )

    fotografia = FotografiaField(
        required=False,
        allow_null=True
    )

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
            'fecha_ingreso_agrupacion',
            'estado',
            'motivo_ingreso_agrupacion',
            'fecha_salida',
            'elenco',
            'cedula',
            'apellidos',
            'nombres',
            'genero',
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
            'fotografia_drive_id',
            'autorizado_publicacion',
            'fecha_autorizacion_publicacion',
        ]

        read_only_fields = ['id', 'fotografia_drive_id']

    def validate(self, attrs):
        errors = {}
        if self.instance is None and 'inscripcion' not in attrs:
            errors['inscripcion'] = 'Este campo es obligatorio al crear un bailarín.'
        for indicador, campo in (
            ('estudia', 'institucion_estudio'),
            ('trabaja', 'lugar_trabajo'),
        ):
            activo = attrs.get(
                indicador, getattr(self.instance, indicador, False)
            )
            valor = attrs.get(campo, getattr(self.instance, campo, None))
            if activo and (not valor or not valor.strip()):
                errors[campo] = 'Este campo es obligatorio cuando {} es verdadero.'.format(
                    indicador
                )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        inscripcion_data = validated_data.pop('inscripcion')
        fotografia = validated_data.pop('fotografia', None)
        if fotografia is not None:
            fotografia_drive = upload_bailarin_photo(
                fotografia
            )
            validated_data['fotografia'] = fotografia_drive['name']
            validated_data['fotografia_drive_id'] = fotografia_drive['id']
        bailarin = super().create(validated_data)
        Inscripcion.objects.create(
            bailarin=bailarin,
            **inscripcion_data
        )
        return bailarin

    @transaction.atomic
    def update(self, instance, validated_data):
        inscripcion_data = validated_data.pop('inscripcion', None)
        fotografia = validated_data.get('fotografia')
        if fotografia is not None:
            fotografia_drive = upload_bailarin_photo(
                fotografia
            )
            validated_data['fotografia'] = fotografia_drive['name']
            validated_data['fotografia_drive_id'] = fotografia_drive['id']
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
