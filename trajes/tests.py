import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import AdquisicionTraje, ComposicionTraje, PrendaTraje, TipoTraje


class InventarioTrajesTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media)
        self.settings_override = override_settings(MEDIA_ROOT=self.media)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.user = get_user_model().objects.create_superuser(
            username='inventario', password='prueba'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.traje = TipoTraje.objects.create(
            nombre='Traje', variante='Mujer', region_cultura='Andina'
        )
        self.prenda = PrendaTraje.objects.create(nombre_prenda='Sombrero')

    def test_tipos_crear_actualizar_y_inactivar(self):
        respuesta = self.client.post('/api/trajes/tipos/', {
            'nombre': 'Danza', 'variante': 'Infantil', 'region_cultura': 'Sierra'
        }, format='json')
        self.assertEqual(respuesta.status_code, 201)
        pk = respuesta.data['id']
        self.assertEqual(self.client.get(f'/api/trajes/tipos/{pk}/').status_code, 200)
        respuesta = self.client.patch(f'/api/trajes/tipos/{pk}/', {
            'descripcion': 'Descripción actualizada'
        }, format='json')
        self.assertEqual(respuesta.status_code, 200)
        respuesta = self.client.post(f'/api/trajes/tipos/{pk}/inactivar/')
        self.assertEqual(respuesta.data['estado'], 'INACTIVO')
        self.assertEqual(self.client.delete(f'/api/trajes/tipos/{pk}/').status_code, 405)

    def test_prenda_compartida_costos_por_traje_y_restricciones(self):
        otro = TipoTraje.objects.create(nombre='Otro', variante='Hombre', region_cultura='Costa')
        for traje, cantidad, precio in (
            (self.traje, 2, '12.30'), (otro, 3, '10.00')
        ):
            respuesta = self.client.post('/api/trajes/composiciones/', {
                'tipo_traje': traje.id, 'prenda': self.prenda.id,
                'cantidad_requerida': cantidad, 'precio_unitario': precio,
            }, format='json')
            self.assertEqual(respuesta.status_code, 201, respuesta.data)
        duplicado = self.client.post('/api/trajes/composiciones/', {
            'tipo_traje': self.traje.id, 'prenda': self.prenda.id, 'cantidad_requerida': 1
        }, format='json')
        self.assertEqual(duplicado.status_code, 400)
        lista = self.client.get(f'/api/trajes/tipos/{self.traje.id}/prendas/')
        self.assertEqual(len(lista.data), 1)
        self.assertEqual(lista.data[0]['prenda_detalle']['nombre_prenda'], 'Sombrero')
        costo = self.client.get(f'/api/trajes/tipos/{self.traje.id}/costo-estimado/')
        self.assertEqual(costo.data['subtotal'], '24.60')
        self.assertTrue(costo.data['completo'])
        self.assertEqual(self.client.delete(f'/api/trajes/prendas/{self.prenda.id}/').status_code, 400)
        self.assertEqual(self.client.get('/api/trajes/composiciones/?tipo_traje=abc').status_code, 400)

    def test_costo_incompleto_y_prendas_inactivas(self):
        faltante = ComposicionTraje.objects.create(
            tipo_traje=self.traje, prenda=self.prenda, cantidad_requerida=1
        )
        costo = self.client.get(f'/api/trajes/tipos/{self.traje.id}/costo-estimado/').data
        self.assertEqual(costo['subtotal'], '0.00')
        self.assertFalse(costo['completo'])
        self.assertEqual(costo['composiciones_sin_precio'], [faltante.pk])
        faltante.estado = 'INACTIVO'
        faltante.save()
        costo = self.client.get(f'/api/trajes/tipos/{self.traje.id}/costo-estimado/').data
        self.assertTrue(costo['completo'])

    def test_crear_editar_y_eliminar_prenda_y_composicion(self):
        respuesta = self.client.post('/api/trajes/prendas/', {
            'nombre_prenda': 'Faja', 'descripcion': 'Tejida'
        }, format='json')
        self.assertEqual(respuesta.status_code, 201)
        prenda_id = respuesta.data['id']
        self.assertEqual(self.client.get(f'/api/trajes/prendas/{prenda_id}/').status_code, 200)
        self.assertEqual(self.client.patch(f'/api/trajes/prendas/{prenda_id}/', {
            'nombre_prenda': 'Faja nueva'
        }, format='json').status_code, 200)
        respuesta = self.client.post('/api/trajes/composiciones/', {
            'tipo_traje': self.traje.id, 'prenda': prenda_id,
            'cantidad_requerida': 1
        }, format='json')
        composicion_id = respuesta.data['id']
        self.assertEqual(self.client.patch(f'/api/trajes/composiciones/{composicion_id}/', {
            'cantidad_requerida': 2, 'precio_unitario': '3.50'
        }, format='json').status_code, 200)
        self.assertEqual(len(self.client.get(
            f'/api/trajes/composiciones/?tipo_traje={self.traje.id}'
        ).data), 1)
        self.assertEqual(self.client.delete(f'/api/trajes/composiciones/{composicion_id}/').status_code, 204)
        self.assertEqual(self.client.delete(f'/api/trajes/prendas/{prenda_id}/').status_code, 204)

    def test_adquisicion_total_actualizacion_y_resumen(self):
        respuesta = self.client.post('/api/trajes/adquisiciones/', {
            'tipo_traje': self.traje.id, 'fecha_adquisicion': '2026-01-02',
            'cantidad_adquirida': 3, 'costo_unitario': '15.20', 'costo_total': '1.00'
        }, format='json')
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        pk = respuesta.data['id']
        self.assertEqual(respuesta.data['costo_total'], '45.60')
        respuesta = self.client.patch(f'/api/trajes/adquisiciones/{pk}/', {
            'cantidad_adquirida': 2
        }, format='json')
        self.assertEqual(respuesta.data['costo_total'], '30.40')
        self.assertEqual(self.client.get(f'/api/trajes/adquisiciones/{pk}/').status_code, 200)
        self.assertEqual(len(self.client.get(
            f'/api/trajes/tipos/{self.traje.id}/adquisiciones/'
        ).data), 1)
        resumen = self.client.get(
            f'/api/trajes/tipos/{self.traje.id}/resumen-adquisiciones/'
        ).data
        self.assertEqual(resumen['cantidad_total_adquirida'], 2)
        self.assertEqual(Decimal(resumen['inversion_total']), Decimal('30.40'))
        self.assertEqual(self.client.delete(f'/api/trajes/adquisiciones/{pk}/').status_code, 405)
        self.assertEqual(AdquisicionTraje.objects.get(pk=pk).costo_total, Decimal('30.40'))

    def test_datos_invalidos_y_comprobante(self):
        base = {
            'tipo_traje': self.traje.id, 'fecha_adquisicion': '2026-01-01',
            'cantidad_adquirida': 0, 'costo_unitario': '-1.00'
        }
        self.assertEqual(self.client.post('/api/trajes/adquisiciones/', base, format='json').status_code, 400)
        base.update({
            'cantidad_adquirida': 1, 'costo_unitario': '1.00',
            'comprobante': SimpleUploadedFile('factura.pdf', b'pdf', content_type='application/pdf')
        })
        respuesta = self.client.post('/api/trajes/adquisiciones/', base, format='multipart')
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertIn('factura', respuesta.data['comprobante'])

    def test_resumen_agrupa_compras_por_traje(self):
        otro = TipoTraje.objects.create(nombre='Otro', variante='Hombre', region_cultura='Costa')
        for traje, cantidad, precio in (
            (self.traje, 2, Decimal('2.25')),
            (self.traje, 3, Decimal('1.10')),
            (otro, 5, Decimal('100.00')),
        ):
            AdquisicionTraje.objects.create(
                tipo_traje=traje, fecha_adquisicion='2026-01-01',
                cantidad_adquirida=cantidad, costo_unitario=precio,
            )
        resumen = self.client.get(f'/api/trajes/tipos/{self.traje.id}/resumen-adquisiciones/').data
        self.assertEqual(resumen['cantidad_total_adquirida'], 5)
        self.assertEqual(Decimal(resumen['inversion_total']), Decimal('7.80'))
        self.assertEqual(len(self.client.get(
            f'/api/trajes/adquisiciones/?tipo_traje={self.traje.id}'
        ).data), 2)

    def test_permisos_en_endpoints_y_acciones_relacionadas(self):
        usuario = get_user_model().objects.create_user(username='lectura')
        usuario.user_permissions.add(Permission.objects.get(
            content_type__app_label='trajes', codename='view_tipotraje'
        ))
        self.client.force_authenticate(usuario)
        self.assertEqual(self.client.get('/api/trajes/tipos/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/trajes/tipos/{self.traje.id}/prendas/').status_code, 403)
        self.assertEqual(self.client.get(f'/api/trajes/tipos/{self.traje.id}/costo-estimado/').status_code, 403)
        self.assertEqual(self.client.get(f'/api/trajes/tipos/{self.traje.id}/resumen-adquisiciones/').status_code, 403)
        self.assertEqual(self.client.post(f'/api/trajes/tipos/{self.traje.id}/inactivar/').status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/trajes/tipos/').status_code, 401)

    def test_inactivar_exige_change_no_add(self):
        usuario = get_user_model().objects.create_user(username='editor')
        usuario.user_permissions.add(Permission.objects.get(
            content_type__app_label='trajes', codename='change_tipotraje'
        ))
        self.client.force_authenticate(usuario)
        self.assertEqual(self.client.post(f'/api/trajes/tipos/{self.traje.id}/inactivar/').status_code, 200)
