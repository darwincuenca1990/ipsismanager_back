from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Bailarin, GrupoFamiliar


@override_settings(TIME_ZONE='UTC')
class CumpleanosBailarinesTests(APITestCase):
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

    def crear_bailarin(self, cedula, fecha):
        return Bailarin.objects.create(
            grupo_familiar=self.grupo,
            elenco=Bailarin.Elenco.INFANTIL,
            cedula=cedula,
            nombres='Nombre',
            apellidos=cedula,
            fecha_nacimiento=fecha,
        )

    @patch('bailarines.views.timezone.localdate', return_value=date(2026, 12, 31))
    def test_semana_cruza_anio_y_esta_ordenada(self, fecha_actual):
        enero = self.crear_bailarin('enero', date(2000, 1, 2))
        domingo = self.crear_bailarin('domingo', date(2001, 12, 27))
        self.crear_bailarin('fuera', date(2000, 1, 3))

        response = self.client.get(reverse('bailarin-cumpleanos-semana'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['fecha_inicio'], '2026-12-27')
        self.assertEqual(response.data['fecha_fin'], '2027-01-02')
        self.assertEqual(
            [item['id'] for item in response.data['data']],
            [domingo.id, enero.id]
        )

    @patch('bailarines.views.timezone.localdate', return_value=date(2026, 11, 10))
    def test_semanas_anterior_y_siguiente(self, fecha_actual):
        anterior = self.crear_bailarin('anterior', date(2000, 11, 7))
        siguiente = self.crear_bailarin('siguiente', date(2000, 11, 15))
        url = reverse('bailarin-cumpleanos-semana')
        response = self.client.get(url, {'semana': 'anterior'})
        self.assertEqual(response.data['fecha_inicio'], '2026-11-01')
        self.assertEqual([item['id'] for item in response.data['data']], [anterior.id])
        response = self.client.get(url, {'semana': 'siguiente'})
        self.assertEqual(response.data['fecha_inicio'], '2026-11-15')
        self.assertEqual([item['id'] for item in response.data['data']], [siguiente.id])
        self.assertEqual(self.client.get(url, {'semana': 'otra'}).status_code, 400)

    @patch('bailarines.views.timezone.localdate', return_value=date(2027, 2, 28))
    def test_semana_no_bisiesta_no_incluye_29_febrero(self, fecha_actual):
        self.crear_bailarin('bisiesto', date(2000, 2, 29))
        response = self.client.get(reverse('bailarin-cumpleanos-semana'))
        self.assertEqual(response.data['data'], [])

    @patch('bailarines.views.timezone.localdate', return_value=date(2028, 2, 28))
    def test_semana_bisiesta_incluye_29_febrero(self, fecha_actual):
        bailarin = self.crear_bailarin('bisiesto', date(2000, 2, 29))
        response = self.client.get(reverse('bailarin-cumpleanos-semana'))
        self.assertEqual([item['id'] for item in response.data['data']], [bailarin.id])

    def test_mes_nombre_numero_y_orden(self):
        fin = self.crear_bailarin('fin', date(2000, 11, 30))
        inicio = self.crear_bailarin('inicio', date(2001, 11, 1))
        self.crear_bailarin('otro', date(2001, 12, 1))
        url = reverse('bailarin-cumpleanos-mes')
        for mes in ('NOVIEMBRE', '11'):
            response = self.client.get(url, {'mes': mes})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['mes'], 11)
            self.assertEqual(
                [item['id'] for item in response.data['data']],
                [inicio.id, fin.id]
            )
        for parametros in ({}, {'mes': '13'}, {'mes': 'abc'}):
            self.assertEqual(self.client.get(url, parametros).status_code, 400)

    def test_mes_febrero_incluye_29(self):
        bailarin = self.crear_bailarin('bisiesto', date(2000, 2, 29))
        response = self.client.get(reverse('bailarin-cumpleanos-mes'), {'mes': 2})
        self.assertEqual([item['id'] for item in response.data['data']], [bailarin.id])

    def test_requiere_permiso_ver_bailarin(self):
        usuario = get_user_model().objects.create_user(username='lector', password='x')
        self.client.force_authenticate(usuario)
        self.assertEqual(
            self.client.get(reverse('bailarin-cumpleanos-semana')).status_code, 403
        )
        self.assertEqual(
            self.client.get(reverse('bailarin-cumpleanos-mes'), {'mes': 11}).status_code,
            403
        )
