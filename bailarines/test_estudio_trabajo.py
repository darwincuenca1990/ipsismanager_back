from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Bailarin, GrupoFamiliar, Inscripcion


class BailarinEstudioTrabajoTests(APITestCase):

    def setUp(self):
        usuario = get_user_model().objects.create_superuser(
            username='admin', password='test'
        )
        self.client.force_authenticate(usuario)
        grupo = GrupoFamiliar.objects.create(
            nombres_completos_representante='Representante',
            celular_representante='0999999999',
            parentesco='Madre'
        )
        self.url = reverse('bailarin-list')
        self.data = {
            'grupo_familiar_id': grupo.pk,
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

    def test_campos_nulos_cuando_no_estudia_ni_trabaja(self):
        response = self.client.post(self.url, {
            **self.data, 'estudia': False, 'trabaja': False,
            'institucion_estudio': None, 'lugar_trabajo': None,
            'referencia_domicilio': None,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        bailarin = Bailarin.objects.get(pk=response.data['id'])
        for campo in ('institucion_estudio', 'lugar_trabajo', 'referencia_domicilio'):
            self.assertIsNone(getattr(bailarin, campo))
            self.assertIsNone(self.client.get(self.url).data[0][campo])

    def test_crear_requiere_valor_si_indicador_es_verdadero(self):
        for indicador, campo in (
            ('estudia', 'institucion_estudio'), ('trabaja', 'lugar_trabajo')
        ):
            for valor in (None, '', '   '):
                with self.subTest(indicador=indicador, valor=valor):
                    response = self.client.post(self.url, {
                        **self.data, indicador: True, campo: valor
                    }, format='json')
                    self.assertEqual(response.status_code, 400, response.data)
                    self.assertIn(campo, response.data)
            response = self.client.post(self.url, {
                **self.data, indicador: True
            }, format='json')
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn(campo, response.data)
        self.assertFalse(Bailarin.objects.exists())

    def test_actualizar_usa_valores_guardados_y_valida_transiciones(self):
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        detalle = reverse('bailarin-detail', args=[response.data['id']])
        response = self.client.patch(
            detalle, {'estudia': True, 'trabaja': True}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('institucion_estudio', response.data)
        self.assertIn('lugar_trabajo', response.data)

        response = self.client.patch(detalle, {
            'estudia': True, 'institucion_estudio': 'Colegio',
            'trabaja': True, 'lugar_trabajo': 'Empresa',
            'referencia_domicilio': None,
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.patch(detalle, {'nombres': 'Otro'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        for campo in ('institucion_estudio', 'lugar_trabajo'):
            response = self.client.patch(detalle, {campo: None}, format='json')
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn(campo, response.data)

        response = self.client.patch(detalle, {
            'estudia': False, 'trabaja': False,
            'institucion_estudio': None, 'lugar_trabajo': None,
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data['institucion_estudio'])
        self.assertIsNone(response.data['lugar_trabajo'])

    def test_put_con_valores_existentes_y_cambios_invalidos(self):
        response = self.client.post(self.url, {
            **self.data, 'estudia': True, 'institucion_estudio': 'Colegio',
            'trabaja': True, 'lugar_trabajo': 'Empresa',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        detalle = reverse('bailarin-detail', args=[response.data['id']])
        response = self.client.put(detalle, {
            **self.data, 'estudia': True, 'trabaja': True,
            'referencia_domicilio': None,
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['institucion_estudio'], 'Colegio')
        self.assertEqual(response.data['lugar_trabajo'], 'Empresa')
        response = self.client.put(detalle, {
            **self.data, 'estudia': True, 'institucion_estudio': None,
            'trabaja': True, 'lugar_trabajo': '',
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('institucion_estudio', response.data)
        self.assertIn('lugar_trabajo', response.data)
