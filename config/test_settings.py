import os
import runpy
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured


SETTINGS_FILE = Path(__file__).resolve().parent / 'settings.py'


class DatabaseSettingsTests(TestCase):
    def load_settings(self, environment):
        with patch.dict(os.environ, environment, clear=True):
            with patch('dotenv.load_dotenv') as load_dotenv:
                settings = runpy.run_path(str(SETTINGS_FILE))
        load_dotenv.assert_called_once_with(SETTINGS_FILE.parent.parent / '.env')
        return settings['DATABASES']['default']

    def test_database_defaults(self):
        self.assertEqual(self.load_settings({}), {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'ipsis',
            'USER': 'ipsis_app',
            'PASSWORD': '',
            'HOST': 'localhost',
            'PORT': '5432',
        })

    def test_database_environment_variables(self):
        self.assertEqual(self.load_settings({
            'DB_NAME': 'test_database',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_password',
            'DB_HOST': 'database',
            'DB_PORT': '5433',
        }), {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'test_database',
            'USER': 'test_user',
            'PASSWORD': 'test_password',
            'HOST': 'database',
            'PORT': '5433',
        })

    def test_dotenv_values_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            dotenv_file = Path(directory) / '.env'
            dotenv_file.write_text(
                'DB_NAME=from_file\nDB_USER=file_user\nDB_PASSWORD=file_password\n',
                encoding='utf-8',
            )
            with patch.dict(os.environ, {'DB_NAME': 'from_environment'}, clear=True):
                with patch('dotenv.load_dotenv', side_effect=lambda path: load_dotenv(dotenv_file)):
                    database = runpy.run_path(str(SETTINGS_FILE))['DATABASES']['default']
        self.assertEqual(database['NAME'], 'from_environment')
        self.assertEqual(database['USER'], 'file_user')
        self.assertEqual(database['PASSWORD'], 'file_password')

    def test_production_requires_secret_and_hosts(self):
        with patch.dict(os.environ, {'DJANGO_DEBUG': 'false'}, clear=True):
            with patch('dotenv.load_dotenv'):
                with self.assertRaises(ImproperlyConfigured):
                    runpy.run_path(str(SETTINGS_FILE))

    def test_production_settings_from_environment(self):
        with patch.dict(os.environ, {
            'DJANGO_DEBUG': 'false',
            'DJANGO_SECRET_KEY': 'test-secret',
            'DJANGO_ALLOWED_HOSTS': 'example.com, www.example.com',
            'DJANGO_CSRF_TRUSTED_ORIGINS': 'https://example.com',
        }, clear=True):
            with patch('dotenv.load_dotenv'):
                settings = runpy.run_path(str(SETTINGS_FILE))
        self.assertFalse(settings['DEBUG'])
        self.assertEqual(settings['SECRET_KEY'], 'test-secret')
        self.assertEqual(settings['ALLOWED_HOSTS'], ['example.com', 'www.example.com'])
        self.assertEqual(settings['CSRF_TRUSTED_ORIGINS'], ['https://example.com'])
        self.assertTrue(settings['SESSION_COOKIE_SECURE'])
        self.assertTrue(settings['CSRF_COOKIE_SECURE'])
