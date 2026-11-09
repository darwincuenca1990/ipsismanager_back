from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import PlantillaCumpleanos


class PlantillaCumpleanosEndpointTests(APITestCase):

    def setUp(self):
        usuario = get_user_model().objects.create_superuser(
            username='admin',
            password='test-password'
        )
        self.client.force_authenticate(usuario)
        self.url = reverse('plantilla-cumpleanos-list')
        self.plantilla_infantil = PlantillaCumpleanos.objects.create(
            elenco=PlantillaCumpleanos.Elenco.INFANTIL,
            mensaje='¡Feliz cumpleaños, {nombre}!'
        )
        PlantillaCumpleanos.objects.create(
            elenco=PlantillaCumpleanos.Elenco.PLANTA,
            mensaje='Sigue creciendo, {nombre}.'
        )

    def test_list_returns_data_envelope_and_display_name(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 2)
        self.assertEqual(
            response.data['data'][0]['elenco_display'],
            'Infantil'
        )
        self.assertEqual(
            response.data['data'][0]['mensaje'],
            '¡Feliz cumpleaños, {nombre}!'
        )

    def test_list_can_filter_by_elenco(self):
        response = self.client.get(self.url, {'elenco': 'INFANTIL'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(
            response.data['data'][0]['id'],
            self.plantilla_infantil.id
        )

    def test_list_rejects_unknown_elenco(self):
        response = self.client.get(self.url, {'elenco': 'DESCONOCIDO'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('elenco', response.data)

    def test_create_rejects_second_template_for_same_elenco(self):
        response = self.client.post(
            self.url,
            {
                'elenco': 'INFANTIL',
                'mensaje': 'Otra plantilla.'
            },
            format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('elenco', response.data)
