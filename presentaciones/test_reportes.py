from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.test import APITestCase

from bailarines.models import Bailarin, GrupoFamiliar

from .models import Presentacion


@patch('presentaciones.views.timezone.localdate', return_value=date(2026, 3, 10))
class ReportesPresentacionesTests(APITestCase):

    def setUp(self):
        usuario = get_user_model().objects.create_superuser(
            username='admin', password='test'
        )
        self.client.force_authenticate(usuario)
        grupo = GrupoFamiliar.objects.create(
            nombres_completos_representante='Representante',
            celular_representante='123', parentesco='Madre'
        )
        self.bailarin = Bailarin.objects.create(
            grupo_familiar=grupo, elenco=Bailarin.Elenco.PLANTA,
            cedula='123', nombres='Nombre', apellidos='Apellido',
            fecha_nacimiento='2000-01-01'
        )
        self.mensual = reverse('presentacion-reporte-mensual')
        self.anual = reverse('presentacion-reporte-anual')

    def crear(self, fecha, bruto, transporte):
        return Presentacion.objects.create(
            fecha=fecha, lugar='Teatro', hora_presentacion='19:30',
            persona_cargo=self.bailarin, costo_total_presentacion=Decimal(bruto),
            costo_transporte=Decimal(transporte), nombre_transporte='Bus',
            tipo_presentacion=Presentacion.Tipo.UN_ELENCO
        )

    def test_mensual_compara_acumulados_e_identificadores(self, fecha_actual):
        primero = self.crear('2026-03-01', '100.10', '20.05')
        segundo = self.crear('2026-03-31', '50.20', '60.10')
        anterior = self.crear('2025-03-15', '40.00', '10.00')
        self.crear('2026-04-01', '1000.00', '0.00')
        self.crear('2025-02-28', '1000.00', '0.00')
        response = self.client.get(self.mensual, {'anio': 2026, 'mes': 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            'mes': 3,
            'actual': {
                'anio': 2026, 'cantidad_presentaciones': 2,
                'ids_presentaciones': [primero.pk, segundo.pk],
                'costo_total_presentacion': '150.30',
                'costo_transporte': '80.15', 'costo_neto': '70.15',
            },
            'anterior': {
                'anio': 2025, 'cantidad_presentaciones': 1,
                'ids_presentaciones': [anterior.pk],
                'costo_total_presentacion': '40.00',
                'costo_transporte': '10.00', 'costo_neto': '30.00',
            },
        })

    def test_anual_mes_actual_incluye_mes_completo_y_comparacion(self, fecha_actual):
        primero = self.crear('2026-01-31', '15.00', '2.00')
        futuro_mismo_mes = self.crear('2026-03-30', '10.00', '15.00')
        self.crear('2026-04-01', '999.00', '0.00')
        anterior = self.crear('2025-03-31', '8.00', '2.00')
        self.crear('2025-04-01', '999.00', '0.00')
        response = self.client.get(self.anual, {'anio': 2026})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['anio'], 2026)
        self.assertEqual(response.data['anio_anterior'], 2025)
        meses = response.data['meses']
        self.assertEqual([item['mes'] for item in meses], [1, 2, 3])
        self.assertEqual(meses[0]['actual']['ids_presentaciones'], [primero.pk])
        self.assertEqual(meses[1]['actual'], {
            'anio': 2026, 'cantidad_presentaciones': 0, 'ids_presentaciones': [],
            'costo_total_presentacion': '0.00', 'costo_transporte': '0.00',
            'costo_neto': '0.00',
        })
        self.assertEqual(meses[2]['actual']['ids_presentaciones'], [futuro_mismo_mes.pk])
        self.assertEqual(meses[2]['actual']['costo_neto'], '-5.00')
        self.assertEqual(meses[2]['anterior']['ids_presentaciones'], [anterior.pk])
        self.assertEqual(meses[2]['anterior']['costo_neto'], '6.00')

    def test_anio_pasado_incluye_diciembre_y_mismo_mes_anterior(self, fecha_actual):
        actual = self.crear('2025-12-31', '21.00', '1.00')
        anterior = self.crear('2024-12-01', '7.00', '2.00')
        response = self.client.get(self.anual, {'anio': 2025})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['meses']), 12)
        diciembre = response.data['meses'][-1]
        self.assertEqual(diciembre['mes'], 12)
        self.assertEqual(diciembre['actual']['ids_presentaciones'], [actual.pk])
        self.assertEqual(diciembre['anterior']['ids_presentaciones'], [anterior.pk])
        self.assertEqual(diciembre['anterior']['anio'], 2024)

    def test_validacion_de_parametros(self, fecha_actual):
        for url, parametros in (
            (self.mensual, {}), (self.mensual, {'anio': 2026}),
            (self.mensual, {'anio': '', 'mes': 1}),
            (self.mensual, {'anio': 1, 'mes': 1}),
            (self.mensual, {'anio': 10000, 'mes': 1}),
            (self.mensual, {'anio': 2026, 'mes': 0}),
            (self.mensual, {'anio': 2026, 'mes': 13}),
            (self.mensual, {'anio': 2026, 'mes': 'a'}),
            (self.anual, {}), (self.anual, {'anio': 1}),
            (self.anual, {'anio': 2027}), (self.anual, {'anio': 'abc'}),
        ):
            with self.subTest(parametros=parametros, url=url):
                self.assertEqual(self.client.get(url, parametros).status_code, 400)
        self.assertEqual(
            self.client.get(self.mensual, {'anio': 2, 'mes': 1}).status_code, 200
        )
        self.assertEqual(
            self.client.get(self.mensual, {'anio': 9999, 'mes': 12}).status_code, 200
        )

    def test_requiere_autenticacion_y_permiso_de_consulta(self, fecha_actual):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.anual, {'anio': 2026}).status_code, 401)
        usuario = get_user_model().objects.create_user(username='lector', password='test')
        self.client.force_authenticate(usuario)
        self.assertEqual(self.client.get(self.anual, {'anio': 2026}).status_code, 403)
        self.assertEqual(
            self.client.get(self.mensual, {'anio': 2026, 'mes': 3}).status_code, 403
        )
        usuario.user_permissions.add(Permission.objects.get(
            content_type__app_label='presentaciones', codename='view_presentacion'
        ))
        self.client.force_authenticate(get_user_model().objects.get(pk=usuario.pk))
        self.assertEqual(self.client.get(self.anual, {'anio': 2026}).status_code, 200)
        self.assertEqual(
            self.client.get(self.mensual, {'anio': 2026, 'mes': 3}).status_code, 200
        )
