from datetime import date
from io import BytesIO
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from PIL import Image

from bailarines.models import Bailarin, GrupoFamiliar, Inscripcion
from .generador_afiches import generar_afiche
from .models import PlantillaCumpleanos
from .services import detectar_cumpleanos


class PlantillaCumpleanosEndpointTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_dir = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.media_dir.cleanup()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.media_settings = override_settings(
            MEDIA_ROOT=self.media_dir.name
        )
        self.media_settings.enable()
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

    def tearDown(self):
        self.media_settings.disable()
        super().tearDown()

    def crear_bailarin(self, **overrides):
        grupo_familiar = GrupoFamiliar.objects.create(
            nombres_completos_representante='Representante',
            celular_representante='0999999999',
            parentesco='Madre'
        )
        datos = {
            'grupo_familiar': grupo_familiar,
            'elenco': Bailarin.Elenco.INFANTIL,
            'cedula': '1234567890',
            'apellidos': 'Pérez',
            'nombres': 'Ana',
            'fecha_nacimiento': date(2010, 11, 9),
            'fotografia': 'ana.jpg',
            'fotografia_drive_id': 'drive-id',
            'autorizado_publicacion': True,
        }
        datos.update(overrides)
        bailarin = Bailarin.objects.create(**datos)
        Inscripcion.objects.create(
            bailarin=bailarin,
            fecha_ingreso_agrupacion=date(2020, 1, 1),
            estado=Inscripcion.Estado.ACTIVO
        )
        return bailarin

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

    @patch('cumpleanos.services.generar_afiche', return_value=b'afiche')
    def test_detector_creates_card_and_is_idempotent(
        self,
        generar_afiche_mock
    ):
        bailarin = self.crear_bailarin()
        fecha = date(2026, 11, 9)

        resultado = detectar_cumpleanos(fecha)

        self.assertEqual(len(resultado['generadas']), 1)
        tarjeta = bailarin.tarjetas_cumpleanos.get(anio=fecha.year)
        self.assertEqual(
            tarjeta.mensaje_generado,
            '¡Feliz cumpleaños, Ana Pérez!'
        )
        self.assertEqual(
            tarjeta.plantilla_utilizada,
            self.plantilla_infantil
        )
        generar_afiche_mock.assert_called_once_with(
            bailarin,
            '¡Feliz cumpleaños, Ana Pérez!'
        )

        segundo_resultado = detectar_cumpleanos(fecha)

        self.assertEqual(segundo_resultado['generadas'], [])
        self.assertEqual(len(segundo_resultado['ya_existentes']), 1)
        self.assertEqual(
            bailarin.tarjetas_cumpleanos.filter(anio=fecha.year).count(),
            1
        )

    @patch('cumpleanos.services.generar_afiche', return_value=b'afiche')
    def test_detector_recovers_card_without_generated_image(
        self,
        generar_afiche_mock
    ):
        bailarin = self.crear_bailarin()
        tarjeta = bailarin.tarjetas_cumpleanos.create(anio=2026)

        resultado = detectar_cumpleanos(date(2026, 11, 9))

        tarjeta.refresh_from_db()
        self.assertEqual(len(resultado['generadas']), 1)
        self.assertTrue(tarjeta.imagen)
        self.assertEqual(
            resultado['generadas'][0]['tarjeta_id'],
            tarjeta.id
        )
        generar_afiche_mock.assert_called_once()

    def test_detector_reports_all_reasons_for_skipped_bailarin(self):
        self.crear_bailarin(
            elenco=Bailarin.Elenco.ASPIRANTE_INFANTIL,
            fotografia='',
            fotografia_drive_id='',
            autorizado_publicacion=False
        )
        bailarin = Bailarin.objects.get(cedula='1234567890')
        bailarin.inscripciones.update(estado=Inscripcion.Estado.INACTIVO)

        resultado = detectar_cumpleanos(date(2026, 11, 9))

        self.assertEqual(resultado['generadas'], [])
        omitida = resultado['omitidas'][0]
        self.assertEqual(
            omitida['mensaje'],
            'PARA EL BAILARIN Ana Pérez NO SE GENERO LA TARJETA POR '
            'LOS SIGUIENTES MOTIVOS: no tiene una inscripción ACTIVO; '
            'no tiene autorización de publicación ACTIVA; no tiene '
            'fotografía registrada; no tiene fotografía de Drive '
            'registrada; no existe una plantilla ACTIVA para el elenco '
            'ASPIRANTE INFANTIL.'
        )

    @patch('cumpleanos.services.generar_afiche', return_value=b'afiche')
    def test_detector_endpoint_runs_detection(self, generar_afiche_mock):
        self.crear_bailarin()

        response = self.client.post(
            reverse('detectar-cumpleanos')
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['generadas']), 1)

    @patch('cumpleanos.generador_afiches.download_bailarin_photo')
    def test_afiche_generator_uses_drive_photo_and_template(
        self,
        download_photo
    ):
        foto = BytesIO()
        Image.new('RGB', (160, 240), color='blue').save(foto, format='JPEG')
        download_photo.return_value = {'content': foto.getvalue()}
        bailarin = self.crear_bailarin()

        contenido = generar_afiche(
            bailarin,
            '¡Feliz cumpleaños, Ana Pérez!'
        )

        download_photo.assert_called_once_with('drive-id')
        afiche = Image.open(BytesIO(contenido))
        self.assertEqual(afiche.format, 'JPEG')
        self.assertEqual(afiche.size, (1080, 1350))
