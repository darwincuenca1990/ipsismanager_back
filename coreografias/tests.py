from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Coreografia


class CoreografiaAPITests(APITestCase):

    def setUp(self):
        self.usuario = get_user_model().objects.create_superuser(
            username='admin', password='test'
        )
        self.client.force_authenticate(self.usuario)
        self.url = reverse('coreografia-list')
        self.data = {
            'nombre': 'Danza',
            'region': 'Sierra',
            'descripcion': 'Descripción de la danza',
            'url_video': 'https://example.com/video',
        }

    def test_crud(self):
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual({key: response.data[key] for key in self.data}, self.data)
        pk = response.data['id']
        detalle = reverse('coreografia-detail', args=[pk])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['id'], pk)
        response = self.client.get(detalle)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['region'], 'Sierra')

        data = {**self.data, 'region': 'Costa'}
        response = self.client.put(detalle, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Coreografia.objects.get(pk=pk).region, 'Costa')
        response = self.client.patch(
            detalle, {'nombre': 'Otra danza'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Coreografia.objects.get(pk=pk).nombre, 'Otra danza')

        response = self.client.delete(detalle)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Coreografia.objects.filter(pk=pk).exists())
        self.assertEqual(self.client.get(detalle).status_code, 404)

    def test_valida_campos_obligatorios_y_url(self):
        for campo in self.data:
            with self.subTest(campo=campo):
                data = self.data.copy()
                del data[campo]
                response = self.client.post(self.url, data, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertIn(campo, response.data)

        response = self.client.post(
            self.url, {**self.data, 'url_video': 'no-es-una-url'}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('url_video', response.data)
        self.assertFalse(Coreografia.objects.exists())

    def test_permisos_por_modelo(self):
        coreografia = Coreografia.objects.create(**self.data)
        detalle = reverse('coreografia-detail', args=[coreografia.pk])
        usuario = get_user_model().objects.create_user(
            username='lector', password='test'
        )
        self.client.force_authenticate(usuario)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(detalle).status_code, 403)
        self.assertEqual(
            self.client.post(self.url, self.data, format='json').status_code, 403
        )
        self.assertEqual(
            self.client.patch(detalle, {'nombre': 'Cambio'}, format='json').status_code,
            403
        )
        self.assertEqual(self.client.delete(detalle).status_code, 403)

        usuario.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='coreografias',
                codename='view_coreografia'
            )
        )
        self.client.force_authenticate(
            get_user_model().objects.get(pk=usuario.pk)
        )
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.get(detalle).status_code, 200)
        self.assertEqual(
            self.client.post(self.url, self.data, format='json').status_code, 403
        )

    def test_requiere_autenticacion(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
