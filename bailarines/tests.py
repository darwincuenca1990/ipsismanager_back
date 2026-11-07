from datetime import date

from django.test import TestCase

from .models import Bailarin, GrupoFamiliar, Inscripcion
from .serializers import BailarinSerializer


class BailarinInscripcionSerializerTests(TestCase):

    def setUp(self):
        self.grupo_familiar = GrupoFamiliar.objects.create(
            nombres_completos_representante='Representante',
            celular_representante='0999999999',
            parentesco='Madre'
        )

    def bailarin_data(self):
        return {
            'grupo_familiar_id': self.grupo_familiar.pk,
            'elenco': Bailarin.Elenco.PLANTA,
            'cedula': '1234567890',
            'apellidos': 'Apellido',
            'nombres': 'Nombre',
            'fecha_nacimiento': '2010-01-01',
            'inscripcion': {
                'fecha_ingreso_agrupacion': '2024-01-01',
                'estado': Inscripcion.Estado.ACTIVO,
            },
        }

    def test_create_bailarin_creates_inscripcion(self):
        serializer = BailarinSerializer(data=self.bailarin_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        bailarin = serializer.save()

        inscripcion = Inscripcion.objects.get(bailarin=bailarin)
        self.assertEqual(inscripcion.estado, Inscripcion.Estado.ACTIVO)
        self.assertEqual(
            inscripcion.fecha_ingreso_agrupacion,
            date(2024, 1, 1)
        )

    def test_create_requires_inscripcion(self):
        data = self.bailarín_data()
        del data['inscripcion']
        serializer = BailarinSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('inscripcion', serializer.errors)

    def test_update_changes_latest_inscripcion_only(self):
        bailarin = Bailarin.objects.create(
            grupo_familiar=self.grupo_familiar,
            elenco=Bailarin.Elenco.PLANTA,
            cedula='1234567890',
            apellidos='Apellido',
            nombres='Nombre',
            fecha_nacimiento=date(2010, 1, 1)
        )
        anterior = Inscripcion.objects.create(
            bailarin=bailarin,
            fecha_ingreso_agrupacion=date(2020, 1, 1),
            estado=Inscripcion.Estado.ACTIVO
        )
        reciente = Inscripcion.objects.create(
            bailarin=bailarin,
            fecha_ingreso_agrupacion=date(2024, 1, 1),
            estado=Inscripcion.Estado.ACTIVO
        )

        serializer = BailarinSerializer(
            bailarin,
            data={'inscripcion': {'estado': Inscripcion.Estado.INACTIVO}},
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        anterior.refresh_from_db()
        reciente.refresh_from_db()
        self.assertEqual(anterior.estado, Inscripcion.Estado.ACTIVO)
        self.assertEqual(reciente.estado, Inscripcion.Estado.INACTIVO)
