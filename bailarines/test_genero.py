from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Bailarin, GrupoFamiliar, Inscripcion


class BailarinGeneroTests(APITestCase):

    def setUp(self):
        usuario = get_user_model().objects.create_superuser(
            username='admin', password='test'
        )
        self.client.force_authenticate(usuario)
        self.grupo = GrupoFamiliar.objects.create(
            nombres_completos_representante='Representante',
            celular_representante='0999999999',
            parentesco='Madre'
        )
        self.url = reverse('bailarin-list')
        self.data = {
            'grupo_familiar_id': self.grupo.pk,
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

    def test_crear_y_listar_genero(self):
        self.data['genero'] = Bailarin.Genero.MASCULINO
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['genero'], 'MASCULINO')
        self.assertEqual(Bailarin.objects.get().genero, 'MASCULINO')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['genero'], 'MASCULINO')

    def test_actualizar_genero(self):
        self.data['genero'] = Bailarin.Genero.MASCULINO
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(response.status_code, 201)
        detalle = reverse('bailarin-detail', args=[response.data['id']])

        response = self.client.patch(
            detalle, {'genero': 'FEMENINO'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['genero'], 'FEMENINO')
        self.assertEqual(Bailarin.objects.get().genero, 'FEMENINO')
        self.assertEqual(self.client.get(detalle).data['genero'], 'FEMENINO')

        self.data['genero'] = 'MASCULINO'
        response = self.client.put(detalle, self.data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Bailarin.objects.get().genero, 'MASCULINO')

    def test_rechaza_genero_invalido_al_crear_y_actualizar(self):
        for genero in ('OTRO', '', 'masculino'):
            with self.subTest(genero=genero):
                response = self.client.post(
                    self.url, {**self.data, 'genero': genero}, format='json'
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn('genero', response.data)

        response = self.client.post(self.url, self.data, format='json')
        detalle = reverse('bailarin-detail', args=[response.data['id']])
        response = self.client.patch(detalle, {'genero': 'OTRO'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('genero', response.data)
        self.assertIsNone(Bailarin.objects.get().genero)

    def test_genero_omitido_se_representa_como_null(self):
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data['genero'])
        self.assertIsNone(self.client.get(self.url).data[0]['genero'])
