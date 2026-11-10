from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Bailarin, GrupoFamiliar


class CandidatosPlantaTests(APITestCase):
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
        self.url = reverse('bailarin-candidatos-elenco-planta')

    def crear_bailarin(self, cedula, fecha, elenco=Bailarin.Elenco.INFANTIL):
        return Bailarin.objects.create(
            grupo_familiar=self.grupo,
            elenco=elenco,
            cedula=cedula,
            nombres='Nombre',
            apellidos=cedula,
            fecha_nacimiento=fecha,
        )

    @patch('bailarines.views.timezone.localdate', return_value=date(2026, 11, 10))
    def test_incluye_limites_y_mayores_excluye_otros_elencos(self, fecha_actual):
        mayor = self.crear_bailarin('mayor', date(2010, 1, 1))
        hoy = self.crear_bailarin('hoy', date(2012, 11, 10))
        limite = self.crear_bailarin('limite', date(2013, 5, 10))
        self.crear_bailarin('tarde', date(2013, 5, 11))
        self.crear_bailarin('planta', date(2010, 1, 1), Bailarin.Elenco.PLANTA)
        self.crear_bailarin('aspirante', date(2010, 1, 1), Bailarin.Elenco.ASPIRANTE_INFANTIL)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['fecha_actual'], '2026-11-10')
        self.assertEqual(response.data['fecha_limite'], '2027-05-10')
        self.assertEqual(
            [item['id'] for item in response.data['data']],
            [mayor.id, hoy.id, limite.id]
        )
        limite.refresh_from_db()
        self.assertEqual(limite.elenco, Bailarin.Elenco.INFANTIL)

    @patch('bailarines.views.timezone.localdate', return_value=date(2025, 8, 31))
    def test_fin_de_mes_y_nacidos_el_29(self, fecha_actual):
        bisiesto = self.crear_bailarin('bisiesto', date(2012, 2, 29))
        self.crear_bailarin('marzo', date(2012, 3, 1))
        response = self.client.get(self.url)
        self.assertEqual(response.data['fecha_limite'], '2026-02-28')
        self.assertEqual([item['id'] for item in response.data['data']], [bisiesto.id])

    @patch('bailarines.views.timezone.localdate', return_value=date(2026, 2, 28))
    def test_29_febrero_cumple_14_en_fecha_actual_no_bisiesta(self, fecha_actual):
        bailarin = self.crear_bailarin('bisiesto', date(2012, 2, 29))
        response = self.client.get(self.url)
        self.assertEqual([item['id'] for item in response.data['data']], [bailarin.id])

    @patch('bailarines.views.timezone.localdate', return_value=date(2027, 8, 29))
    def test_limite_bisiesto_y_anio_nacimiento_no_bisiesto(self, fecha_actual):
        bailarin = self.crear_bailarin('febrero', date(2014, 2, 28))
        self.crear_bailarin('marzo', date(2014, 3, 1))
        response = self.client.get(self.url)
        self.assertEqual(response.data['fecha_limite'], '2028-02-29')
        self.assertEqual([item['id'] for item in response.data['data']], [bailarin.id])

    def test_requiere_permiso_ver_bailarin(self):
        usuario = get_user_model().objects.create_user(username='lector', password='x')
        self.client.force_authenticate(usuario)
        self.assertEqual(self.client.get(self.url).status_code, 403)
