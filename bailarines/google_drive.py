
import logging
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from rest_framework.exceptions import APIException


logger = logging.getLogger(__name__)


class GoogleDriveUploadError(APIException):
    status_code = 503
    default_detail = 'No fue posible completar la operación en Google Drive.'
    default_code = 'google_drive_operation_failed'


class GoogleDriveFileNotFound(APIException):
    status_code = 404
    default_detail = 'No se encontró la fotografía en Google Drive.'
    default_code = 'google_drive_file_not_found'


def get_drive_service():
    try:
        token_file = settings.GOOGLE_DRIVE_TOKEN_FILE
        if not token_file.is_file():
            raise GoogleDriveUploadError(
                'Google Drive aún no está autorizado. Inicia sesión como '
                'superusuario y completa la autorización en '
                '/api/auth/google/authorize/.'
            )

        credentials = Credentials.from_authorized_user_file(
            str(token_file),
            scopes=['https://www.googleapis.com/auth/drive.file']
        )

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            token_file.write_text(
                credentials.to_json(),
                encoding='utf-8'
            )

        drive = build(
            'drive',
            'v3',
            credentials=credentials,
            cache_discovery=False
        )
        return drive

    except (GoogleAuthError, OSError, ValueError) as error:
        logger.exception('Error al autenticar con Google Drive.')
        raise GoogleDriveUploadError() from error


def upload_bailarin_photo(uploaded_file):
    folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    if not folder_id:
        raise ImproperlyConfigured(
            'Configura GOOGLE_DRIVE_FOLDER_ID.'
        )

    try:
        drive = get_drive_service()
        uploaded_file.seek(0)

        media = MediaIoBaseUpload(
            uploaded_file,
            mimetype=uploaded_file.content_type or 'application/octet-stream',
            resumable=True
        )

        response = drive.files().create(
            body={
                'name': uploaded_file.name,
                'parents': [folder_id],
            },
            media_body=media,
            supportsAllDrives=True,
            fields='id,name,mimeType,size'
        ).execute()

        return {
            'id': response['id'],
            'name': response['name'],
        }

    except (GoogleAuthError, HttpError, OSError, ValueError) as error:
        logger.exception(
            'Error al subir fotografía del bailarín a Drive.'
        )
        raise GoogleDriveUploadError() from error


def download_bailarin_photo(file_id):
    try:
        drive = get_drive_service()
        metadata = drive.files().get(
            fileId=file_id,
            fields='name,mimeType',
            supportsAllDrives=True
        ).execute()

        content = BytesIO()
        downloader = MediaIoBaseDownload(
            content,
            drive.files().get_media(
                fileId=file_id,
                supportsAllDrives=True
            )
        )
        done = False
        while not done:
            _, done = downloader.next_chunk()

        return {
            'content': content.getvalue(),
            'name': metadata['name'],
            'mime_type': metadata.get(
                'mimeType',
                'application/octet-stream'
            ),
        }
    except HttpError as error:
        if error.resp.status == 404:
            raise GoogleDriveFileNotFound() from error
        logger.exception('Error al descargar fotografía desde Drive.')
        raise GoogleDriveUploadError() from error
    except (GoogleAuthError, OSError, ValueError) as error:
        logger.exception('Error al descargar fotografía desde Drive.')
        raise GoogleDriveUploadError() from error
