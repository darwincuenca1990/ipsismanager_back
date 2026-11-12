
from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET

from google_auth_oauthlib.flow import Flow
from oauthlib.oauth2.rfc6749.errors import OAuth2Error

from parametros.servicios import obtener_parametro


GOOGLE_DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive.file'
]


def get_google_flow(state=None, code_verifier=None):
    required_settings = (
        'GOOGLE_OAUTH_CLIENT_ID',
        'GOOGLE_OAUTH_CLIENT_SECRET',
        'GOOGLE_OAUTH_REDIRECT_URI',
    )
    valores = {
        nombre: obtener_parametro(nombre) for nombre in required_settings
    }
    missing_settings = [
        nombre for nombre, valor in valores.items() if not valor
    ]
    if missing_settings:
        raise ImproperlyConfigured(
            'Faltan configuraciones OAuth de Google: '
            + ', '.join(missing_settings)
        )

    redirect_uri = valores['GOOGLE_OAUTH_REDIRECT_URI']
    client_config = {
        'web': {
            'client_id': valores['GOOGLE_OAUTH_CLIENT_ID'],
            'client_secret': valores['GOOGLE_OAUTH_CLIENT_SECRET'],
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': [redirect_uri],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=GOOGLE_DRIVE_SCOPES,
        state=state,
        code_verifier=code_verifier
    )

    flow.redirect_uri = redirect_uri

    return flow


@staff_member_required(login_url='/admin/login/')
@require_GET
def google_drive_authorize(request):

    if not request.user.is_superuser:
        return HttpResponse('No autorizado.', status=403)

    flow = get_google_flow()

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    request.session['google_oauth_state'] = state
    request.session['google_oauth_code_verifier'] = flow.code_verifier

    return redirect(authorization_url)


@staff_member_required(login_url='/admin/login/')
@require_GET
def google_drive_callback(request):

    if not request.user.is_superuser:
        return HttpResponse('No autorizado.', status=403)

    state = request.session.pop('google_oauth_state', None)
    code_verifier = request.session.pop(
        'google_oauth_code_verifier',
        None
    )

    if not state or request.GET.get('state') != state:
        return HttpResponse(
            'Estado OAuth inválido. Intenta nuevamente.',
            status=400
        )

    if not code_verifier:
        return HttpResponse(
            'La sesión de autorización expiró o está incompleta. '
            'Inicia nuevamente desde /api/auth/google/authorize/.',
            status=400
        )

    if request.GET.get('error'):
        return HttpResponse(
            'No se autorizó el acceso a Google Drive.',
            status=400
        )

    code = request.GET.get('code')
    if not code:
        return HttpResponse(
            'Google no devolvió el código de autorización. '
            'Inicia nuevamente el proceso.',
            status=400
        )

    flow = get_google_flow(
        state=state,
        code_verifier=code_verifier
    )
    try:
        flow.fetch_token(code=code)
    except OAuth2Error as error:
        error_code = getattr(error, 'error', 'oauth_error')
        return HttpResponse(
            'Google rechazó el código de autorización '
            f'({error_code}). Inicia nuevamente desde '
            '/api/auth/google/authorize/ y verifica que el URI de '
            'redirección coincida exactamente con el registrado en Google.',
            status=400
        )

    credentials = flow.credentials

    if not credentials.refresh_token:
        return HttpResponse(
            'Google no devolvió un refresh token. '
            'Vuelve a autorizar la aplicación.',
            status=400
        )

    token_file = Path(settings.GOOGLE_DRIVE_TOKEN_FILE)

    token_file.parent.mkdir(parents=True, exist_ok=True)

    token_file.write_text(
        credentials.to_json(),
        encoding='utf-8'
    )

    return HttpResponse(
        '¡IPSIS Manager se conectó correctamente con Google Drive!'
    )
