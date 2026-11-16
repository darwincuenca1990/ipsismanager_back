from datetime import date, datetime, timezone as datetime_timezone
from io import BytesIO
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from PIL import Image

from bailarines.models import Bailarin, GrupoFamiliar, Inscripcion
from .generador_afiches import generar_afiche
from .models import PlantillaCumpleanos, PublicacionRedSocial
from .services import FacebookAPIError, detectar_cumpleanos


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
        bailarin = self.crear_bailarin()

        with patch('cumpleanos.services.timezone.localdate', return_value=date(2026, 11, 9)):
            response = self.client.post(reverse('detectar-cumpleanos'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['generadas']), 1)
        tarjeta = bailarin.tarjetas_cumpleanos.get(anio=2026)
        self.assertEqual(response.data['generadas'][0]['tarjeta_id'], tarjeta.id)
        self.assertEqual(tarjeta.estado_generacion, 'GENERADA')
        self.assertTrue(tarjeta.imagen)
        self.assertIsNotNone(tarjeta.fecha_generacion)
        self.assertEqual(tarjeta.plantilla_utilizada, self.plantilla_infantil)
        self.assertEqual(tarjeta.mensaje_generado, '¡Feliz cumpleaños, Ana Pérez!')
        self.assertEqual(tarjeta.motivo_no_generacion, '')

    @patch('cumpleanos.services.generar_afiche', return_value=b'afiche')
    def test_detector_endpoint_reports_already_generated_cards(self, generar_afiche_mock):
        bailarin = self.crear_bailarin()
        with patch(
            'cumpleanos.services.timezone.localdate',
            return_value=date(2026, 11, 9)
        ):
            primera = self.client.post(reverse('detectar-cumpleanos'))
            segunda = self.client.post(reverse('detectar-cumpleanos'))

        self.assertEqual(primera.status_code, 200)
        self.assertEqual(segunda.status_code, 200)
        tarjeta = bailarin.tarjetas_cumpleanos.get(anio=2026)
        self.assertEqual(segunda.data['generadas'], [])
        self.assertEqual(segunda.data['omitidas'], [])
        self.assertEqual(segunda.data['ya_existentes'][0]['tarjeta_id'], tarjeta.id)
        self.assertEqual(
            segunda.data['ya_existentes'][0]['mensaje'],
            'La tarjeta de cumpleaños de Ana Pérez para el año 2026 '
            'ya se encuentra realizada.'
        )
        self.assertEqual(
            segunda.data['mensaje'],
            'Las tarjetas de cumpleaños para el año 2026 '
            'ya se encuentran realizadas.'
        )
        generar_afiche_mock.assert_called_once()

    @patch('cumpleanos.services.generar_afiche', return_value=b'afiche')
    def test_detector_reports_existing_and_generates_other_cards(self, generar_afiche_mock):
        bailarin = self.crear_bailarin()
        detectar_cumpleanos(date(2026, 11, 9))
        otro = self.crear_bailarin(cedula='9876543210', nombres='Luis')
        with patch(
            'cumpleanos.services.timezone.localdate',
            return_value=date(2026, 11, 9)
        ):
            response = self.client.post(reverse('detectar-cumpleanos'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['ya_existentes'][0]['bailarin_id'], bailarin.id)
        self.assertIn('ya se encuentra realizada', response.data['ya_existentes'][0]['mensaje'])
        self.assertEqual(response.data['generadas'][0]['bailarin_id'], otro.id)
        self.assertNotIn('mensaje', response.data)
        self.assertEqual(generar_afiche_mock.call_count, 2)

    def test_detector_endpoint_records_missing_requirements(self):
        bailarin = self.crear_bailarin(autorizado_publicacion=False)
        with patch('cumpleanos.services.timezone.localdate', return_value=date(2026, 11, 9)):
            response = self.client.post(reverse('detectar-cumpleanos'))

        self.assertEqual(response.status_code, 200)
        tarjeta = bailarin.tarjetas_cumpleanos.get(anio=2026)
        self.assertEqual(response.data['omitidas'][0]['tarjeta_id'], tarjeta.id)
        self.assertEqual(tarjeta.estado_generacion, 'NO_GENERADA')
        self.assertIn('autorización', tarjeta.motivo_no_generacion)
        self.assertFalse(tarjeta.imagen)

    @patch('cumpleanos.services.generar_afiche', return_value=b'afiche')
    def test_detector_records_storage_failure(self, generar_afiche_mock):
        bailarin = self.crear_bailarin()
        with patch('cumpleanos.services.timezone.localdate', return_value=date(2026, 11, 9)):
            with patch('django.db.models.fields.files.FieldFile.save', side_effect=OSError('disco lleno')):
                response = self.client.post(reverse('detectar-cumpleanos'))

        self.assertEqual(response.status_code, 200)
        tarjeta = bailarin.tarjetas_cumpleanos.get(anio=2026)
        self.assertEqual(response.data['omitidas'][0]['tarjeta_id'], tarjeta.id)
        self.assertEqual(tarjeta.estado_generacion, 'NO_GENERADA')
        self.assertIn('disco lleno', tarjeta.motivo_no_generacion)
        self.assertEqual(tarjeta.mensaje_generado, '¡Feliz cumpleaños, Ana Pérez!')
        self.assertIsNone(tarjeta.fecha_generacion)

    @patch('cumpleanos.services.generar_afiche', return_value=b'afiche')
    def test_existing_card_is_preserved_when_requirements_change(self, generar_afiche_mock):
        bailarin = self.crear_bailarin()
        fecha = date(2026, 11, 9)
        detectar_cumpleanos(fecha)
        tarjeta = bailarin.tarjetas_cumpleanos.get(anio=2026)
        bailarin.autorizado_publicacion = False
        bailarin.save(update_fields=['autorizado_publicacion'])

        resultado = detectar_cumpleanos(fecha)

        self.assertEqual(resultado['omitidas'], [])
        self.assertEqual(resultado['ya_existentes'][0]['tarjeta_id'], tarjeta.id)
        tarjeta.refresh_from_db()
        self.assertEqual(tarjeta.estado_generacion, 'GENERADA')
        generar_afiche_mock.assert_called_once()

    @patch('cumpleanos.services.generar_afiche', return_value=b'afiche')
    def test_detector_creates_a_new_card_each_year(self, generar_afiche_mock):
        bailarin = self.crear_bailarin()
        detectar_cumpleanos(date(2026, 11, 9))
        detectar_cumpleanos(date(2027, 11, 9))

        self.assertEqual(
            set(bailarin.tarjetas_cumpleanos.values_list('anio', flat=True)),
            {2026, 2027}
        )
        self.assertEqual(generar_afiche_mock.call_count, 2)

    def test_skipped_bailarin_is_recorded_as_not_generated(self):
        bailarin = self.crear_bailarin(autorizado_publicacion=False)

        detectar_cumpleanos(date(2026, 11, 9))

        tarjeta = bailarin.tarjetas_cumpleanos.get(anio=2026)
        self.assertEqual(tarjeta.estado_generacion, 'NO_GENERADA')
        self.assertIn('autorización', tarjeta.motivo_no_generacion)

    @patch('cumpleanos.services.generar_afiche', side_effect=OSError('boom'))
    def test_generation_failure_is_recorded_then_recovered(self, mock):
        bailarin = self.crear_bailarin()

        resultado = detectar_cumpleanos(date(2026, 11, 9))

        self.assertEqual(len(resultado['omitidas']), 1)
        tarjeta = bailarin.tarjetas_cumpleanos.get(anio=2026)
        self.assertEqual(tarjeta.estado_generacion, 'NO_GENERADA')
        self.assertIn('boom', tarjeta.motivo_no_generacion)

        with patch(
            'cumpleanos.services.generar_afiche',
            return_value=b'afiche'
        ):
            detectar_cumpleanos(date(2026, 11, 9))
        tarjeta.refresh_from_db()
        self.assertEqual(tarjeta.estado_generacion, 'GENERADA')
        self.assertEqual(tarjeta.motivo_no_generacion, '')
        self.assertIsNotNone(tarjeta.fecha_generacion)

    def crear_tarjeta_generada(self):
        bailarin = self.crear_bailarin()
        return bailarin.tarjetas_cumpleanos.create(
            anio=2026,
            estado_generacion='GENERADA'
        )

    @patch('cumpleanos.views.publicar_fotografia_facebook')
    def test_approve_records_user_and_date(self, publicar):
        tarjeta = self.crear_tarjeta_generada()
        tarjeta.imagen.save('afiche.jpeg', ContentFile(b'afiche'))
        tarjeta.mensaje_generado = 'Feliz cumpleaños'
        tarjeta.save()
        publicar.return_value = {
            'id': 'foto-123', 'post_id': 'post-123', 'publicada': True
        }

        response = self.client.post(
            reverse('tarjeta-cumpleanos-aprobar', args=[tarjeta.id])
        )

        self.assertEqual(response.status_code, 200)
        tarjeta.refresh_from_db()
        self.assertEqual(tarjeta.estado, 'APROBADA')
        self.assertEqual(tarjeta.aprobado_por.username, 'admin')
        self.assertIsNotNone(tarjeta.fecha_aprobacion)
        self.assertEqual(response.data['data'][0]['estado'], 'APROBADA')
        publicacion = PublicacionRedSocial.objects.get(tarjeta=tarjeta)
        self.assertEqual(publicacion.plataforma, 'FACEBOOK')
        self.assertEqual(publicacion.estado, 'PUBLICADA')
        self.assertEqual(publicacion.texto_publicacion, 'Feliz cumpleaños')
        self.assertEqual(publicacion.id_publicacion_externa, 'post-123')
        self.assertEqual(publicacion.fecha_publicacion, tarjeta.fecha_aprobacion)
        self.assertEqual(publicar.call_args.args[1:], ('afiche.jpeg', 'Feliz cumpleaños'))

        again = self.client.post(
            reverse('tarjeta-cumpleanos-aprobar', args=[tarjeta.id])
        )
        self.assertEqual(again.status_code, 400)
        publicar.assert_called_once()

    @patch('cumpleanos.views.publicar_fotografia_facebook')
    def test_failed_publication_leaves_card_pending(self, publicar):
        tarjeta = self.crear_tarjeta_generada()
        tarjeta.imagen.save('afiche.jpeg', ContentFile(b'afiche'))
        publicar.side_effect = FacebookAPIError('Facebook no disponible.')

        response = self.client.post(
            reverse('tarjeta-cumpleanos-aprobar', args=[tarjeta.id])
        )

        self.assertEqual(response.status_code, 502)
        self.assertIn('Facebook no disponible.', str(response.data))
        tarjeta.refresh_from_db()
        self.assertEqual(tarjeta.estado, 'PENDIENTE')
        self.assertIsNone(tarjeta.fecha_aprobacion)
        self.assertIsNone(tarjeta.aprobado_por)
        self.assertFalse(tarjeta.publicaciones.exists())

    @patch('cumpleanos.views.publicar_fotografia_facebook')
    def test_approve_without_image_does_not_publish(self, publicar):
        tarjeta = self.crear_tarjeta_generada()
        response = self.client.post(
            reverse('tarjeta-cumpleanos-aprobar', args=[tarjeta.id])
        )
        self.assertEqual(response.status_code, 400)
        publicar.assert_not_called()
        self.assertFalse(tarjeta.publicaciones.exists())

    @patch('cumpleanos.views.publicar_fotografia_facebook')
    def test_unconfirmed_publication_leaves_card_pending(self, publicar):
        tarjeta = self.crear_tarjeta_generada()
        tarjeta.imagen.save('afiche.jpeg', ContentFile(b'afiche'))
        publicar.return_value = {'id': 'foto-123', 'publicada': False}

        response = self.client.post(
            reverse('tarjeta-cumpleanos-aprobar', args=[tarjeta.id])
        )

        self.assertEqual(response.status_code, 502)
        tarjeta.refresh_from_db()
        self.assertEqual(tarjeta.estado, 'PENDIENTE')
        self.assertFalse(tarjeta.publicaciones.exists())

    @patch('cumpleanos.views.publicar_fotografia_facebook')
    def test_existing_pending_publication_is_updated(self, publicar):
        tarjeta = self.crear_tarjeta_generada()
        tarjeta.imagen.save('afiche.jpeg', ContentFile(b'afiche'))
        publicacion = PublicacionRedSocial.objects.create(
            tarjeta=tarjeta, plataforma='FACEBOOK', estado='ERROR',
            mensaje_error='Error anterior'
        )
        publicar.return_value = {'id': 'foto-123', 'post_id': None, 'publicada': True}

        response = self.client.post(
            reverse('tarjeta-cumpleanos-aprobar', args=[tarjeta.id])
        )

        self.assertEqual(response.status_code, 200)
        publicacion.refresh_from_db()
        self.assertEqual(publicacion.estado, 'PUBLICADA')
        self.assertEqual(publicacion.id_publicacion_externa, 'foto-123')
        self.assertEqual(publicacion.mensaje_error, '')
        self.assertEqual(tarjeta.publicaciones.count(), 1)

    @patch('cumpleanos.views.publicar_fotografia_facebook')
    def test_existing_published_record_prevents_duplicate_post(self, publicar):
        tarjeta = self.crear_tarjeta_generada()
        tarjeta.imagen.save('afiche.jpeg', ContentFile(b'afiche'))
        PublicacionRedSocial.objects.create(
            tarjeta=tarjeta, plataforma='FACEBOOK', estado='PUBLICADA',
            id_publicacion_externa='post-123'
        )
        response = self.client.post(
            reverse('tarjeta-cumpleanos-aprobar', args=[tarjeta.id])
        )
        self.assertEqual(response.status_code, 400)
        publicar.assert_not_called()
        tarjeta.refresh_from_db()
        self.assertEqual(tarjeta.estado, 'PENDIENTE')

    def test_reject_requires_reason_and_records_data(self):
        tarjeta = self.crear_tarjeta_generada()
        url = reverse('tarjeta-cumpleanos-rechazar', args=[tarjeta.id])

        self.assertEqual(self.client.post(url, {}).status_code, 400)
        response = self.client.post(url, {'motivo': 'Foto borrosa'})

        self.assertEqual(response.status_code, 200)
        tarjeta.refresh_from_db()
        self.assertEqual(tarjeta.estado, 'RECHAZADA')
        self.assertEqual(tarjeta.motivo_rechazo, 'Foto borrosa')
        self.assertEqual(tarjeta.rechazado_por.username, 'admin')
        self.assertIsNotNone(tarjeta.fecha_rechazo)

    def test_cannot_review_not_generated_card(self):
        bailarin = self.crear_bailarin()
        tarjeta = bailarin.tarjetas_cumpleanos.create(anio=2026)

        response = self.client.post(
            reverse('tarjeta-cumpleanos-aprobar', args=[tarjeta.id])
        )

        self.assertEqual(response.status_code, 400)

    def test_approve_requires_permission(self):
        tarjeta = self.crear_tarjeta_generada()
        usuario = get_user_model().objects.create_user(
            username='lector',
            password='x'
        )
        self.client.force_authenticate(usuario)

        response = self.client.post(
            reverse('tarjeta-cumpleanos-aprobar', args=[tarjeta.id])
        )

        self.assertEqual(response.status_code, 403)

    def test_list_cards_filters_by_state(self):
        self.crear_tarjeta_generada()

        response = self.client.get(
            reverse('tarjeta-cumpleanos-list'),
            {'estado_generacion': 'NO_GENERADA'}
        )

        self.assertEqual(response.data['data'], [])

    def crear_publicaciones_para_filtros(self):
        tarjeta = self.crear_tarjeta_generada()
        otras_tarjetas = [
            tarjeta.bailarin.tarjetas_cumpleanos.create(anio=anio)
            for anio in (2025, 2027, 2028)
        ]
        datos = [
            (tarjeta, 'PUBLICADA', datetime(2026, 11, 1, tzinfo=datetime_timezone.utc)),
            (otras_tarjetas[0], 'ERROR', datetime(2026, 11, 30, 23, 59, tzinfo=datetime_timezone.utc)),
            (otras_tarjetas[1], 'PUBLICADA', datetime(2025, 11, 15, tzinfo=datetime_timezone.utc)),
            (otras_tarjetas[2], 'ERROR', None),
        ]
        return [
            PublicacionRedSocial.objects.create(
                tarjeta=tarjeta, plataforma='FACEBOOK',
                estado=estado, fecha_publicacion=fecha
            )
            for tarjeta, estado, fecha in datos
        ]

    @override_settings(TIME_ZONE='UTC')
    @patch('cumpleanos.views.timezone.localdate', return_value=date(2026, 11, 10))
    def test_publicaciones_month_year_and_status(self, fecha_actual):
        publicaciones = self.crear_publicaciones_para_filtros()
        url = reverse('publicacion-red-social-list')
        response = self.client.get(url, {
            'mes_desde': 'noviembre', 'mes_hasta': 'NOVIEMBRE'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item['id'] for item in response.data['data']},
            {publicaciones[0].id, publicaciones[1].id}
        )
        response = self.client.get(url, {
            'mes_desde': '10', 'mes_hasta': '12', 'anio': 2025, 'estado': 'PUBLICADA'
        })
        self.assertEqual([item['id'] for item in response.data['data']], [publicaciones[2].id])
        response = self.client.get(url, {'estado': 'ERROR'})
        self.assertEqual(
            {item['id'] for item in response.data['data']},
            {publicaciones[1].id, publicaciones[3].id}
        )

    @override_settings(TIME_ZONE='UTC')
    def test_publicaciones_month_range_and_retrieve(self):
        publicaciones = self.crear_publicaciones_para_filtros()
        response = self.client.get(reverse('publicacion-red-social-list'), {
            'anio': 2026, 'mes_desde': 'octubre', 'mes_hasta': 'diciembre'
        })
        self.assertEqual(
            {item['id'] for item in response.data['data']},
            {publicaciones[0].id, publicaciones[1].id}
        )
        self.assertEqual(response.data['data'][0]['tarjeta'], publicaciones[1].tarjeta_id)
        response = self.client.get(
            reverse('publicacion-red-social-detail', args=[publicaciones[0].id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data'][0]['id'], publicaciones[0].id)

    def test_publicaciones_invalid_filters(self):
        url = reverse('publicacion-red-social-list')
        for filtros in (
            {'mes_desde': 'inventado', 'mes_hasta': '12'},
            {'mes_desde': '1', 'mes_hasta': '13'}, {'estado': 'OTRO'},
            {'anio': '0'}, {'fecha_desde': '2026-11-01'},
            {'mes_desde': '12', 'mes_hasta': '11'},
            {'mes_desde': 'noviembre'}, {'mes_hasta': '11'}, {'mes': '11'},
        ):
            with self.subTest(filtros=filtros):
                self.assertEqual(self.client.get(url, filtros).status_code, 400)

    def test_publicaciones_requires_view_permission(self):
        usuario = get_user_model().objects.create_user(username='lector', password='x')
        self.client.force_authenticate(usuario)
        self.assertEqual(
            self.client.get(reverse('publicacion-red-social-list')).status_code, 403
        )

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
