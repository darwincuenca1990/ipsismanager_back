from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models.deletion import ProtectedError
from django.urls import reverse
from rest_framework.test import APITestCase

from bailarines.models import Bailarin, GrupoFamiliar
from coreografias.models import Coreografia

from .models import Presentacion


class PresentacionAPITests(APITestCase):

    def setUp(self):
        usuario = get_user_model().objects.create_superuser(
            username='admin', password='test'
        )
        self.client.force_authenticate(usuario)
        grupo = GrupoFamiliar.objects.create(
            nombres_completos_representante='Representante',
            celular_representante='123', parentesco='Madre'
        )
        self.bailarines = [
            Bailarin.objects.create(
                grupo_familiar=grupo, elenco=Bailarin.Elenco.PLANTA,
                cedula=str(i), nombres='Nombre', apellidos=str(i),
                fecha_nacimiento='2000-01-01'
            ) for i in range(2)
        ]
        self.coreografias = [
            Coreografia.objects.create(
                nombre=str(i), region='Sierra', descripcion='Descripción',
                url_video='https://example.com/video'
            ) for i in range(2)
        ]
        self.url = reverse('presentacion-list')
        self.data = {
            'fecha': '2026-11-25',
            'lugar': 'Teatro Central',
            'hora_presentacion': '19:30:00',
            'persona_cargo': self.bailarines[0].pk,
            'costo_total_presentacion': '500.00',
            'costo_transporte': '100.00',
            'nombre_transporte': 'Bus',
            'tipo_presentacion': 'FESTIVALIPSIS',
            'elencos': ['INFANTIL', 'PLANTA'],
            'bitacora': [
                {
                    'bailarin': self.bailarines[0].pk,
                    'coreografias': [coreografia.pk for coreografia in self.coreografias],
                },
                {'bailarin': self.bailarines[1].pk, 'coreografias': []},
            ],
        }

    def crear(self, data=None):
        response = self.client.post(
            self.url, self.data if data is None else data, format='json'
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def test_crear_listar_consultar_y_actualizar_bitacora(self):
        response = self.crear()
        pk = response.data['id']
        self.assertEqual(response.data['costo_neto'], '400.00')
        self.assertEqual(response.data['elencos'], ['INFANTIL', 'PLANTA'])
        self.assertEqual(response.data['bitacora'], self.data['bitacora'])
        detalle = reverse('presentacion-detail', args=[pk])
        self.assertEqual(self.client.get(self.url).data[0]['bitacora'], self.data['bitacora'])
        self.assertEqual(self.client.get(detalle).data['bitacora'], self.data['bitacora'])

        response = self.client.patch(
            detalle, {'costo_transporte': '125.25'}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['costo_neto'], '374.75')
        self.assertEqual(response.data['bitacora'], self.data['bitacora'])

        bitacora = [{
            'bailarin': self.bailarines[1].pk,
            'coreografias': [self.coreografias[1].pk],
        }]
        response = self.client.patch(
            detalle, {'tipo_presentacion': 'UN ELENCO', 'elencos': ['PLANTA'],
                      'bitacora': bitacora}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['elencos'], ['PLANTA'])
        self.assertEqual(self.client.get(detalle).data['bitacora'], bitacora)
        self.assertEqual(Presentacion.objects.get(pk=pk).bitacora.count(), 1)

        data = {**self.data, 'bitacora': []}
        response = self.client.put(detalle, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['bitacora'], [])
        self.assertEqual(self.client.delete(detalle).status_code, 405)

    def test_crear_sin_bitacora(self):
        data = self.data.copy()
        del data['bitacora']
        response = self.crear(data)
        self.assertEqual(response.data['bitacora'], [])

    def test_filtros_independientes_y_combinados(self):
        primera = self.crear()
        self.crear({**self.data, 'fecha': '2025-11-01', 'lugar': 'Otro lugar'})
        self.crear({**self.data, 'fecha': '2026-12-01', 'lugar': 'Teatro'})
        for parametros, cantidad in [
            ({'mes': 11}, 2), ({'anio': 2026}, 2), ({'lugar': 'teatro'}, 2),
            ({'mes': 11, 'anio': 2026, 'lugar': 'CENTRAL'}, 1),
        ]:
            with self.subTest(parametros=parametros):
                response = self.client.get(self.url, parametros)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.data), cantidad)
                if cantidad == 1:
                    self.assertEqual(response.data[0]['id'], primera.data['id'])
        for parametros in (
            {'mes': 13}, {'mes': 'a'}, {'mes': ''}, {'anio': 0}, {'lugar': ''}
        ):
            with self.subTest(parametros=parametros):
                self.assertEqual(self.client.get(self.url, parametros).status_code, 400)

    def test_validacion_y_actualizacion_atomica(self):
        response = self.crear()
        detalle = reverse('presentacion-detail', args=[response.data['id']])
        invalidos = [
            {'persona_cargo': 999999},
            {'costo_transporte': '-1.00'},
            {'tipo_presentacion': 'UN ELENCO'},
            {'elencos': ['PLANTA', 'PLANTA']},
            {'elencos': ['NO EXISTE']},
            {'bitacora': [{'bailarin': self.bailarines[0].pk}]},
            {'bitacora': [{'coreografias': []}]},
            {'bitacora': [{'bailarin': 999999, 'coreografias': []}]},
            {'bitacora': [{'bailarin': self.bailarines[0].pk, 'coreografias': [999999]}]},
            {'bitacora': [self.data['bitacora'][0], self.data['bitacora'][0]]},
            {'bitacora': [{'bailarin': self.bailarines[0].pk,
                           'coreografias': [self.coreografias[0].pk] * 2}]},
        ]
        for cambio in invalidos:
            with self.subTest(cambio=cambio):
                response = self.client.patch(
                    detalle, {'lugar': 'Cambio', **cambio}, format='json'
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertEqual(Presentacion.objects.get().lugar, 'Teatro Central')
                self.assertEqual(self.client.get(detalle).data['bitacora'], self.data['bitacora'])

    def test_error_al_guardar_bitacora_revierte_toda_la_actualizacion(self):
        response = self.crear()
        detalle = reverse('presentacion-detail', args=[response.data['id']])
        with patch(
            'presentaciones.serializers.Bitacora.objects.create',
            side_effect=RuntimeError('Error de prueba')
        ):
            with self.assertRaises(RuntimeError):
                self.client.patch(
                    detalle, {'lugar': 'Cambio', 'bitacora': self.data['bitacora']},
                    format='json'
                )
        self.assertEqual(Presentacion.objects.get().lugar, 'Teatro Central')
        self.assertEqual(self.client.get(detalle).data['bitacora'], self.data['bitacora'])

    def test_proteccion_de_referencias(self):
        self.crear()
        with self.assertRaises(ProtectedError):
            self.bailarines[0].delete()
        with self.assertRaises(ProtectedError):
            self.coreografias[0].delete()
        self.assertEqual(self.client.delete(
            reverse('bailarin-detail', args=[self.bailarines[0].pk])
        ).status_code, 400)
        self.assertEqual(self.client.delete(
            reverse('coreografia-detail', args=[self.coreografias[0].pk])
        ).status_code, 400)

    def test_autenticacion_y_permisos(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
        usuario = get_user_model().objects.create_user(username='lector', password='test')
        self.client.force_authenticate(usuario)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.data, format='json').status_code, 403)
        usuario.user_permissions.add(Permission.objects.get(
            content_type__app_label='presentaciones', codename='view_presentacion'
        ))
        self.client.force_authenticate(get_user_model().objects.get(pk=usuario.pk))
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url, self.data, format='json').status_code, 403)
