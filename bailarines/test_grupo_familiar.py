from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import GrupoFamiliar


class GrupoFamiliarCamposPapaTests(APITestCase):

    def setUp(self):
        usuario = get_user_model().objects.create_superuser(
            username='admin', password='test'
        )
        self.client.force_authenticate(usuario)
        self.url = reverse('grupo-familiar-list')
        self.campos_papa = (
            'apellidos_papa', 'nombres_papa', 'celular_papa',
            'lugar_trabajo_papa',
        )
        self.data = {
            'nombres_completos_representante': 'Representante',
            'celular_representante': '0999999999',
            'parentesco': 'Madre',
        }

    def test_crear_y_listar_con_campos_del_padre_null(self):
        data = {**self.data, **dict.fromkeys(self.campos_papa)}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        grupo = GrupoFamiliar.objects.get(pk=response.data['id'])
        listado = self.client.get(self.url)
        self.assertEqual(listado.status_code, 200)
        for campo in self.campos_papa:
            with self.subTest(campo=campo):
                self.assertIsNone(response.data[campo])
                self.assertIsNone(getattr(grupo, campo))
                self.assertIsNone(listado.data[0][campo])

    def test_actualizar_campos_del_padre_a_null(self):
        data = {**self.data, **dict.fromkeys(self.campos_papa, 'Valor')}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        detalle = reverse('grupo-familiar-detail', args=[response.data['id']])

        response = self.client.patch(
            detalle, dict.fromkeys(self.campos_papa), format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        grupo = GrupoFamiliar.objects.get(pk=response.data['id'])
        for campo in self.campos_papa:
            with self.subTest(campo=campo):
                self.assertIsNone(response.data[campo])
                self.assertIsNone(getattr(grupo, campo))

        response = self.client.put(
            detalle, {**self.data, **dict.fromkeys(self.campos_papa)},
            format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(all(response.data[campo] is None for campo in self.campos_papa))

    def test_campos_del_padre_siguen_permitiendo_omision_y_texto_vacio(self):
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        detalle = reverse('grupo-familiar-detail', args=[response.data['id']])
        response = self.client.patch(
            detalle, dict.fromkeys(self.campos_papa, ''), format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(all(response.data[campo] == '' for campo in self.campos_papa))


class GrupoFamiliarCamposMamaTests(APITestCase):

    def setUp(self):
        usuario = get_user_model().objects.create_superuser(
            username='admin', password='test'
        )
        self.client.force_authenticate(usuario)
        self.url = reverse('grupo-familiar-list')
        self.campos_mama = (
            'apellidos_mama', 'nombres_mama', 'celular_mama',
            'lugar_trabajo_mama',
        )
        self.data = {
            'nombres_completos_representante': 'Representante',
            'celular_representante': '0999999999',
            'parentesco': 'Padre',
        }

    def test_crear_y_listar_con_campos_de_la_madre_null(self):
        response = self.client.post(
            self.url, {**self.data, **dict.fromkeys(self.campos_mama)}, format='json'
        )
        self.assertEqual(response.status_code, 201, response.data)
        grupo = GrupoFamiliar.objects.get(pk=response.data['id'])
        listado = self.client.get(self.url)
        self.assertEqual(listado.status_code, 200)
        for campo in self.campos_mama:
            with self.subTest(campo=campo):
                self.assertIsNone(response.data[campo])
                self.assertIsNone(getattr(grupo, campo))
                self.assertIsNone(listado.data[0][campo])

    def test_actualizar_campos_de_la_madre_a_null(self):
        response = self.client.post(
            self.url, {**self.data, **dict.fromkeys(self.campos_mama, 'Valor')},
            format='json'
        )
        self.assertEqual(response.status_code, 201, response.data)
        detalle = reverse('grupo-familiar-detail', args=[response.data['id']])
        response = self.client.patch(
            detalle, dict.fromkeys(self.campos_mama), format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        grupo = GrupoFamiliar.objects.get(pk=response.data['id'])
        for campo in self.campos_mama:
            with self.subTest(campo=campo):
                self.assertIsNone(response.data[campo])
                self.assertIsNone(getattr(grupo, campo))
        response = self.client.put(
            detalle, {**self.data, **dict.fromkeys(self.campos_mama)}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(all(response.data[campo] is None for campo in self.campos_mama))

    def test_campos_de_la_madre_permiten_omision_y_texto_vacio(self):
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        detalle = reverse('grupo-familiar-detail', args=[response.data['id']])
        response = self.client.patch(
            detalle, dict.fromkeys(self.campos_mama, ''), format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(all(response.data[campo] == '' for campo in self.campos_mama))
