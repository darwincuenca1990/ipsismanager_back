from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from .google_drive import (
    GoogleDriveUploadError,
    download_bailarin_photo,
    get_drive_service,
    upload_bailarin_photo,
)
from .models import Bailarin, GrupoFamiliar, Inscripcion
from .serializers import (
    BailarinInscripcionSerializer,
    BailarinSerializer,
)


class BailarinInscripcionInputTests(SimpleTestCase):

    def test_accepts_json_string_for_multipart_payload(self):
        serializer = BailarinInscripcionSerializer(
            data=(
                '{"fecha_ingreso_agrupacion":"2024-01-15",'
                '"estado":"ACTIVO"}'
            )
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data['estado'],
            Inscripcion.Estado.ACTIVO
        )


class GoogleDriveUploadTests(SimpleTestCase):

    @override_settings(
        GOOGLE_DRIVE_TOKEN_FILE=Path('google_drive_token.json')
    )
    @patch('bailarines.google_drive.build')
    @patch(
        'bailarines.google_drive.Credentials.from_authorized_user_file'
    )
    @patch('pathlib.Path.is_file', return_value=True)
    def test_drive_service_returns_built_client(
        self,
        token_exists,
        credentials_factory,
        build
    ):
        drive = MagicMock()
        build.return_value = drive
        credentials_factory.return_value.expired = False

        service = get_drive_service()

        self.assertIs(service, drive)

    @override_settings(
        GOOGLE_DRIVE_TOKEN_FILE=Path('missing_google_drive_token.json'),
        GOOGLE_DRIVE_FOLDER_ID='shared-folder-id'
    )
    def test_missing_oauth_token_returns_authorization_message(self):
        with self.assertRaises(GoogleDriveUploadError) as error:
            upload_bailarin_photo(
                SimpleUploadedFile('foto.png', b'image bytes')
            )

        self.assertIn('aún no está autorizado', str(error.exception.detail))

    @override_settings(
        GOOGLE_DRIVE_TOKEN_FILE=Path('google_drive_token.json'),
        GOOGLE_DRIVE_FOLDER_ID='shared-folder-id'
    )
    @patch('bailarines.google_drive.get_drive_service')
    def test_uploads_file_to_configured_shared_drive_folder(
            self,
            get_drive_service
    ):
        drive = MagicMock()
        get_drive_service.return_value = drive
        drive.files.return_value.create.return_value.execute.return_value = {
            'id': 'drive-file-id',
            'name': 'foto.png',
        }
        uploaded_file = SimpleUploadedFile(
            'foto.png',
            b'image bytes',
            content_type='image/png'
        )

        photo = upload_bailarin_photo(uploaded_file)

        self.assertEqual(
            photo,
            {'id': 'drive-file-id', 'name': 'foto.png'}
        )
        get_drive_service.assert_called_once()
        drive.files.return_value.create.assert_called_once()
        call_args = drive.files.return_value.create.call_args
        self.assertEqual(
            call_args.kwargs['body'],
            {'name': 'foto.png', 'parents': ['shared-folder-id']}
        )
        self.assertTrue(call_args.kwargs['supportsAllDrives'])
        drive.files.return_value.create.return_value.execute.assert_called_once()

    def test_drive_file_id_is_exposed_as_read_only(self):
        serializer = BailarinSerializer()

        self.assertTrue(serializer.fields['fotografia_drive_id'].read_only)


class GoogleDriveDownloadTests(SimpleTestCase):

    @patch('bailarines.google_drive.MediaIoBaseDownload')
    @patch('bailarines.google_drive.get_drive_service')
    def test_downloads_photo_and_returns_mime_type(
        self,
        get_drive_service,
        downloader_class
    ):
        drive = MagicMock()
        get_drive_service.return_value = drive
        drive.files.return_value.get.return_value.execute.return_value = {
            'name': 'foto.png',
            'mimeType': 'image/png',
        }
        downloader = downloader_class.return_value
        downloader.next_chunk.return_value = (None, True)

        photo = download_bailarin_photo('drive-file-id')

        self.assertEqual(photo['name'], 'foto.png')
        self.assertEqual(photo['mime_type'], 'image/png')
        self.assertEqual(photo['content'], b'')
        drive.files.return_value.get.assert_called_once_with(
            fileId='drive-file-id',
            fields='name,mimeType',
            supportsAllDrives=True
        )
        drive.files.return_value.get_media.assert_called_once_with(
            fileId='drive-file-id',
            supportsAllDrives=True
        )


class BailarinInscripcionSerializerTests(TestCase):

    def setUp(self):
        self.grupo_familiar = GrupoFamiliar.objects.create(
            nombres_completos_representante='Representante',
            celular_representante='0999999999',
            parentesco='Madre'
        )

    def bailarin_data(self):
        return {
            'grupo_familiar_id': self.grupo_familiar.pk,
            'elenco': Bailarin.Elenco.PLANTA,
            'cedula': '1234567890',
            'apellidos': 'Apellido',
            'nombres': 'Nombre',
            'fecha_nacimiento': '2010-01-01',
            'inscripcion': {
                'fecha_ingreso_agrupacion': '2024-01-01',
                'estado': Inscripcion.Estado.ACTIVO,
            },
        }

    def test_create_bailarin_creates_inscripcion(self):
        serializer = BailarinSerializer(data=self.bailarin_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        bailarin = serializer.save()

        inscripcion = Inscripcion.objects.get(bailarin=bailarin)
        self.assertEqual(inscripcion.estado, Inscripcion.Estado.ACTIVO)
        self.assertEqual(
            inscripcion.fecha_ingreso_agrupacion,
            date(2024, 1, 1)
        )

    def test_create_requires_inscripcion(self):
        data = self.bailarín_data()
        del data['inscripcion']
        serializer = BailarinSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('inscripcion', serializer.errors)

    def test_update_changes_latest_inscripcion_only(self):
        bailarin = Bailarin.objects.create(
            grupo_familiar=self.grupo_familiar,
            elenco=Bailarin.Elenco.PLANTA,
            cedula='1234567890',
            apellidos='Apellido',
            nombres='Nombre',
            fecha_nacimiento=date(2010, 1, 1)
        )
        anterior = Inscripcion.objects.create(
            bailarin=bailarin,
            fecha_ingreso_agrupacion=date(2020, 1, 1),
            estado=Inscripcion.Estado.ACTIVO
        )
        reciente = Inscripcion.objects.create(
            bailarin=bailarin,
            fecha_ingreso_agrupacion=date(2024, 1, 1),
            estado=Inscripcion.Estado.ACTIVO
        )

        serializer = BailarinSerializer(
            bailarin,
            data={'inscripcion': {'estado': Inscripcion.Estado.INACTIVO}},
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        anterior.refresh_from_db()
        reciente.refresh_from_db()
        self.assertEqual(anterior.estado, Inscripcion.Estado.ACTIVO)
        self.assertEqual(reciente.estado, Inscripcion.Estado.INACTIVO)
