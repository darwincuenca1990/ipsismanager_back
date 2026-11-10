from io import BytesIO
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from .services import (
    FacebookAPIError,
    obtener_configuracion_facebook,
    obtener_url_graph,
    publicar_fotografia_facebook,
    verificar_conexion_facebook,
)


@override_settings(
    FACEBOOK_APP_ID='app-id',
    FACEBOOK_APP_SECRET='app-secret',
    FACEBOOK_PAGE_ID='page-id',
    FACEBOOK_PAGE_ACCESS_TOKEN='page-token',
    FACEBOOK_API_VERSION='v26.0',
)
class FacebookServiceTests(SimpleTestCase):

    def test_configuracion_y_url(self):
        self.assertEqual(obtener_url_graph(), 'https://graph.facebook.com/v26.0')
        self.assertEqual(obtener_configuracion_facebook(), {
            'app_id': 'app-id',
            'app_secret': 'app-secret',
            'page_id': 'page-id',
            'page_token': 'page-token',
        })

    @override_settings(FACEBOOK_APP_SECRET='', FACEBOOK_PAGE_ID=None)
    def test_configuracion_faltante(self):
        with self.assertRaisesMessage(
            FacebookAPIError, 'app_secret, page_id'
        ):
            obtener_configuracion_facebook()

    @patch('cumpleanos.services.requests.get')
    def test_verificar_conexion(self, get):
        get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'id': 'page-id', 'name': 'Pagina'})
        )
        self.assertEqual(verificar_conexion_facebook(), {
            'id': 'page-id',
            'nombre': 'Pagina',
            'conectado': True,
        })
        get.assert_called_once_with(
            'https://graph.facebook.com/v26.0/page-id',
            params={'fields': 'id,name', 'access_token': 'page-token'},
            timeout=30
        )

    @patch('cumpleanos.services.requests.post')
    def test_publicar_fotografia_jpeg(self, post):
        archivo = BytesIO(b'contenido')
        archivo.seek(3)

        def responder(*args, **kwargs):
            self.assertEqual(archivo.tell(), 0)
            self.assertEqual(kwargs['files']['source'], (
                'afiche.jpeg', archivo, 'image/jpeg'
            ))
            return Mock(
                status_code=200,
                json=Mock(return_value={'id': 'foto', 'post_id': 'post'})
            )

        post.side_effect = responder
        self.assertEqual(
            publicar_fotografia_facebook(archivo, 'afiche.jpeg', 'Mensaje'),
            {'id': 'foto', 'post_id': 'post', 'publicada': True}
        )
        self.assertEqual(
            post.call_args.args[0],
            'https://graph.facebook.com/v26.0/page-id/photos'
        )
        self.assertEqual(post.call_args.kwargs['data'], {
            'caption': 'Mensaje',
            'published': 'true',
            'access_token': 'page-token',
        })
        self.assertEqual(post.call_args.kwargs['timeout'], 120)

    @patch('cumpleanos.services.requests.get')
    def test_error_de_comunicacion(self, get):
        get.side_effect = requests.Timeout()
        with self.assertRaisesMessage(
            FacebookAPIError, 'No fue posible comunicarse con Facebook.'
        ):
            verificar_conexion_facebook()

    @patch('cumpleanos.services.requests.post')
    def test_error_de_publicacion(self, post):
        post.return_value = Mock(
            status_code=400,
            json=Mock(return_value={'error': {'code': 10, 'message': 'Error'}})
        )
        with self.assertRaisesMessage(
            FacebookAPIError, 'Facebook no pudo publicar la fotografía.'
        ):
            publicar_fotografia_facebook(BytesIO(b'foto'), 'foto.png', 'Hola')

    @patch('cumpleanos.services.requests.get')
    def test_respuestas_invalidas_o_rechazadas(self, get):
        for status, resultado in [
            (200, {'error': {'message': 'Error'}}),
            (200, {'id': 'page-id'}),
            (200, []),
            (500, {}),
        ]:
            with self.subTest(status=status, resultado=resultado):
                get.return_value = Mock(
                    status_code=status, json=Mock(return_value=resultado)
                )
                with self.assertRaises(FacebookAPIError):
                    verificar_conexion_facebook()
        get.return_value = Mock(
            status_code=200, json=Mock(side_effect=ValueError('JSON inválido'))
        )
        with self.assertRaises(FacebookAPIError):
            verificar_conexion_facebook()

    @patch('cumpleanos.services.requests.post')
    def test_publicacion_sin_id_no_se_considera_exitosa(self, post):
        post.return_value = Mock(status_code=200, json=Mock(return_value={}))
        with self.assertRaises(FacebookAPIError):
            publicar_fotografia_facebook(BytesIO(b'foto'), 'foto.png', 'Hola')
