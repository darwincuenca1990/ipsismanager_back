import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from .google_oauth import google_drive_callback


class GoogleDriveCallbackTests(SimpleTestCase):

    @override_settings(
        GOOGLE_DRIVE_TOKEN_FILE=Path(tempfile.gettempdir())
        / 'ipsis-google-drive-test-token.json'
    )
    @patch('usuarios.google_oauth.get_google_flow')
    def test_exchanges_authorization_code_without_parsing_http_callback(
        self,
        get_flow
    ):
        token_path = Path(tempfile.gettempdir()) / (
            'ipsis-google-drive-test-token.json'
        )
        self.addCleanup(token_path.unlink, missing_ok=True)

        flow = MagicMock()
        flow.credentials.refresh_token = 'refresh-token'
        flow.credentials.to_json.return_value = '{"token":"test"}'
        get_flow.return_value = flow

        request = RequestFactory().get(
            '/api/auth/google/callback/',
            {'state': 'valid-state', 'code': 'authorization-code'}
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_staff=True,
            is_superuser=True
        )
        request.session = {
            'google_oauth_state': 'valid-state',
            'google_oauth_code_verifier': 'stored-code-verifier'
        }

        response = google_drive_callback(request)

        self.assertEqual(response.status_code, 200)
        flow.fetch_token.assert_called_once_with(code='authorization-code')
        get_flow.assert_called_once_with(
            state='valid-state',
            code_verifier='stored-code-verifier'
        )
        self.assertNotIn('google_oauth_state', request.session)
        self.assertNotIn('google_oauth_code_verifier', request.session)
        self.assertTrue(token_path.is_file())

    def test_requires_authorization_code(self):
        request = RequestFactory().get(
            '/api/auth/google/callback/',
            {'state': 'valid-state'}
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_staff=True,
            is_superuser=True
        )
        request.session = {
            'google_oauth_state': 'valid-state',
            'google_oauth_code_verifier': 'stored-code-verifier'
        }

        response = google_drive_callback(request)

        self.assertEqual(response.status_code, 400)

    @patch('usuarios.google_oauth.get_google_flow')
    def test_requires_new_auth_when_code_verifier_is_missing(self, get_flow):
        request = RequestFactory().get(
            '/api/auth/google/callback/',
            {'state': 'valid-state', 'code': 'authorization-code'}
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_staff=True,
            is_superuser=True
        )
        request.session = {'google_oauth_state': 'valid-state'}

        response = google_drive_callback(request)

        self.assertEqual(response.status_code, 400)
        get_flow.assert_not_called()

    @patch('usuarios.google_oauth.get_google_flow')
    def test_returns_client_error_when_google_rejects_token_exchange(
        self,
        get_flow
    ):
        flow = MagicMock()
        flow.fetch_token.side_effect = InvalidGrantError()
        get_flow.return_value = flow
        request = RequestFactory().get(
            '/api/auth/google/callback/',
            {'state': 'valid-state', 'code': 'authorization-code'}
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_staff=True,
            is_superuser=True
        )
        request.session = {
            'google_oauth_state': 'valid-state',
            'google_oauth_code_verifier': 'stored-code-verifier'
        }

        response = google_drive_callback(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn(b'invalid_grant', response.content)
