import logging
import mimetypes

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from bailarines.models import Bailarin, Inscripcion
from parametros.servicios import obtener_parametro
from .generador_afiches import generar_afiche
from .models import PlantillaCumpleanos, TarjetaCumpleanos


logger = logging.getLogger(__name__)


class FacebookAPIError(Exception):
    pass


def obtener_url_graph():
    version = obtener_parametro('FACEBOOK_API_VERSION', 'v26.0')
    return f'https://graph.facebook.com/{version}'


def obtener_configuracion_facebook():
    configuracion = {
        'app_id': obtener_parametro('FACEBOOK_APP_ID'),
        'app_secret': obtener_parametro('FACEBOOK_APP_SECRET'),
        'page_id': obtener_parametro('FACEBOOK_PAGE_ID'),
        'page_token': obtener_parametro('FACEBOOK_PAGE_ACCESS_TOKEN'),
    }
    faltantes = [
        nombre for nombre, valor in configuracion.items() if not valor
    ]
    if faltantes:
        raise FacebookAPIError(
            'Faltan configuraciones de Facebook: ' + ', '.join(faltantes)
        )
    return configuracion


def _resultado_facebook(response):
    try:
        resultado = response.json()
    except ValueError as error:
        logger.error('Facebook devolvió una respuesta JSON inválida.')
        raise FacebookAPIError(
            'Facebook devolvió una respuesta inválida.'
        ) from error

    if not isinstance(resultado, dict):
        logger.error('Facebook devolvió una respuesta inesperada.')
        raise FacebookAPIError('Facebook devolvió una respuesta inválida.')
    return resultado


def verificar_conexion_facebook():
    config = obtener_configuracion_facebook()
    url = f"{obtener_url_graph()}/{config['page_id']}"
    try:
        response = requests.get(
            url,
            params={
                'fields': 'id,name',
                'access_token': config['page_token'],
            },
            timeout=30
        )
    except requests.RequestException as error:
        logger.error('Error de comunicación con Facebook.')
        raise FacebookAPIError(
            'No fue posible comunicarse con Facebook.'
        ) from error

    resultado = _resultado_facebook(response)
    if response.status_code >= 400 or 'error' in resultado:
        logger.error('Facebook rechazó la verificación de página.')
        raise FacebookAPIError(
            'No fue posible verificar la página de Facebook.'
        )
    if not resultado.get('id') or not resultado.get('name'):
        logger.error('Facebook devolvió datos de página incompletos.')
        raise FacebookAPIError('Facebook devolvió una respuesta inválida.')
    return {
        'id': resultado['id'],
        'nombre': resultado['name'],
        'conectado': True,
    }


def publicar_fotografia_facebook(archivo, nombre_archivo, mensaje):
    """Publica una fotografía en la página desde un archivo binario abierto."""
    config = obtener_configuracion_facebook()
    url = f"{obtener_url_graph()}/{config['page_id']}/photos"
    tipo_archivo = mimetypes.guess_type(nombre_archivo)[0]
    try:
        archivo.seek(0)
        response = requests.post(
            url,
            data={
                'caption': mensaje,
                'published': 'true',
                'access_token': config['page_token'],
            },
            files={
                'source': (
                    nombre_archivo,
                    archivo,
                    tipo_archivo or 'application/octet-stream',
                ),
            },
            timeout=120
        )
    except requests.RequestException as error:
        logger.error('Error de comunicación al publicar en Facebook.')
        raise FacebookAPIError(
            'No fue posible confirmar la publicación en Facebook. '
            'Verifique la página antes de reintentar.'
        ) from error

    resultado = _resultado_facebook(response)
    if response.status_code >= 400 or 'error' in resultado:
        error_meta = resultado.get('error')
        if not isinstance(error_meta, dict):
            error_meta = {}
        logger.error(
            'Facebook rechazó la publicación. Código: %s. Subcódigo: %s. '
            'Mensaje: %s',
            error_meta.get('code'),
            error_meta.get('error_subcode'),
            error_meta.get('message')
        )
        raise FacebookAPIError('Facebook no pudo publicar la fotografía.')
    if not resultado.get('id'):
        logger.error('Facebook devolvió datos de publicación incompletos.')
        raise FacebookAPIError('Facebook devolvió una respuesta inválida.')
    return {
        'id': resultado['id'],
        'post_id': resultado.get('post_id'),
        'publicada': True,
    }


def _registrar_no_generada(bailarin, anio, plantilla, motivo, mensaje=None):
    tarjeta, _ = TarjetaCumpleanos.objects.get_or_create(
        bailarin=bailarin,
        anio=anio
    )
    if tarjeta.imagen:
        return tarjeta

    tarjeta.estado_generacion = TarjetaCumpleanos.EstadoGeneracion.NO_GENERADA
    tarjeta.motivo_no_generacion = motivo
    tarjeta.plantilla_utilizada = plantilla
    if mensaje is not None:
        tarjeta.mensaje_generado = mensaje
    tarjeta.save(update_fields=[
        'estado_generacion',
        'motivo_no_generacion',
        'plantilla_utilizada',
        'mensaje_generado',
        'actualizado_en',
    ])
    return tarjeta


def _registrar_existente(resultado, tarjeta, nombre):
    resultado['ya_existentes'].append({
        'bailarin_id': tarjeta.bailarin_id,
        'bailarin': nombre,
        'tarjeta_id': tarjeta.id,
        'imagen': tarjeta.imagen.url,
        'mensaje': (
            f'La tarjeta de cumpleaños de {nombre} para el año '
            f'{tarjeta.anio} ya se encuentra realizada.'
        ),
    })


def generar_tarjeta_manual(tarjeta):
    """Reintenta generar el afiche de una tarjeta NO_GENERADA.

    Devuelve la tarjeta actualizada o lanza ValidationError con los motivos.
    """
    bailarin = tarjeta.bailarin
    ultima = Inscripcion.objects.filter(
        bailarin=bailarin
    ).order_by('-fecha_ingreso_agrupacion', '-id').first()
    plantilla = PlantillaCumpleanos.objects.filter(
        activa=True,
        elenco=bailarin.elenco
    ).first()

    motivos = []
    if not ultima or ultima.estado != Inscripcion.Estado.ACTIVO:
        motivos.append('no tiene una inscripción ACTIVO')
    if not bailarin.autorizado_publicacion:
        motivos.append('no tiene autorización de publicación ACTIVA')
    if not bailarin.fotografia or not bailarin.fotografia.strip():
        motivos.append('no tiene fotografía registrada')
    if (
        not bailarin.fotografia_drive_id
        or not bailarin.fotografia_drive_id.strip()
    ):
        motivos.append('no tiene fotografía de Drive registrada')
    if plantilla is None:
        motivos.append(
            f'no existe una plantilla ACTIVA para el elenco {bailarin.elenco}'
        )
    if motivos:
        texto = '; '.join(motivos)
        _registrar_no_generada(bailarin, tarjeta.anio, plantilla, texto)
        raise ValidationError(
            f'No se pudo generar la tarjeta: {texto}.'
        )

    nombre = f'{bailarin.nombres} {bailarin.apellidos}'.strip()
    mensaje = plantilla.mensaje.replace('{nombre}', nombre)
    try:
        contenido = generar_afiche(bailarin, mensaje)
    except (APIException, OSError, ValueError) as error:
        motivo = f'error al generar el afiche: {getattr(error, "detail", error)}'
        _registrar_no_generada(
            bailarin, tarjeta.anio, plantilla, motivo, mensaje
        )
        raise ValidationError(f'No se pudo generar la tarjeta: {motivo}.')

    tarjeta.imagen.save(
        f'afiche_{bailarin.id}_{tarjeta.anio}.jpeg',
        ContentFile(contenido),
        save=False
    )
    tarjeta.mensaje_generado = mensaje
    tarjeta.plantilla_utilizada = plantilla
    tarjeta.estado_generacion = TarjetaCumpleanos.EstadoGeneracion.GENERADA
    tarjeta.motivo_no_generacion = ''
    tarjeta.fecha_generacion = timezone.now()
    tarjeta.save()
    return tarjeta


def detectar_cumpleanos(fecha=None):
    fecha = fecha or timezone.localdate()
    ultima_inscripcion = Inscripcion.objects.filter(
        bailarin_id=OuterRef('pk')
    ).order_by(
        '-fecha_ingreso_agrupacion',
        '-id'
    )
    bailarines = Bailarin.objects.filter(
        fecha_nacimiento__month=fecha.month,
        fecha_nacimiento__day=fecha.day
    ).annotate(
        estado_inscripcion_actual=Subquery(
            ultima_inscripcion.values('estado')[:1]
        )
    )

    plantillas = {
        plantilla.elenco: plantilla
        for plantilla in PlantillaCumpleanos.objects.filter(
            activa=True
        )
    }

    resultado = {
        'fecha': fecha.isoformat(),
        'generadas': [],
        'omitidas': [],
        'ya_existentes': [],
    }

    for bailarin in bailarines:
        nombre_completo = f'{bailarin.nombres} {bailarin.apellidos}'.strip()
        tarjeta_existente = TarjetaCumpleanos.objects.filter(
            bailarin=bailarin,
            anio=fecha.year
        ).first()
        if tarjeta_existente and tarjeta_existente.imagen:
            _registrar_existente(resultado, tarjeta_existente, nombre_completo)
            continue

        motivos = []

        if bailarin.estado_inscripcion_actual != Inscripcion.Estado.ACTIVO:
            motivos.append('no tiene una inscripción ACTIVO')

        if not bailarin.autorizado_publicacion:
            motivos.append('no tiene autorización de publicación ACTIVA')

        if not bailarin.fotografia or not bailarin.fotografia.strip():
            motivos.append('no tiene fotografía registrada')

        if (
            not bailarin.fotografia_drive_id
            or not bailarin.fotografia_drive_id.strip()
        ):
            motivos.append('no tiene fotografía de Drive registrada')

        plantilla = plantillas.get(bailarin.elenco)
        if plantilla is None:
            motivos.append(
                f'no existe una plantilla ACTIVA para el elenco '
                f'{bailarin.elenco}'
            )

        if motivos:
            texto_motivos = '; '.join(motivos)
            tarjeta = _registrar_no_generada(
                bailarin,
                fecha.year,
                plantilla,
                texto_motivos
            )
            resultado['omitidas'].append({
                'bailarin_id': bailarin.id,
                'bailarin': nombre_completo,
                'tarjeta_id': tarjeta.id,
                'mensaje': (
                    f'PARA EL BAILARIN {nombre_completo} NO SE GENERO '
                    f'LA TARJETA POR LOS SIGUIENTES MOTIVOS: '
                    f'{texto_motivos}.'
                ),
                'motivos': motivos,
            })
            continue

        mensaje = plantilla.mensaje.replace(
            '{nombre}',
            nombre_completo
        )
        tarjeta, _ = TarjetaCumpleanos.objects.get_or_create(
            bailarin=bailarin,
            anio=fecha.year,
            defaults={
                'plantilla_utilizada': plantilla,
                'mensaje_generado': mensaje,
            }
        )
        if tarjeta.imagen:
            _registrar_existente(resultado, tarjeta, nombre_completo)
            continue

        try:
            contenido_afiche = generar_afiche(bailarin, mensaje)
            tarjeta.imagen.save(
                f'afiche_{bailarin.id}_{fecha.year}.jpeg',
                ContentFile(contenido_afiche),
                save=False
            )
        except (APIException, OSError, ValueError) as error:
            motivo = (
                f'error al generar el afiche: '
                f'{getattr(error, "detail", error)}'
            )
            tarjeta = _registrar_no_generada(
                bailarin,
                fecha.year,
                plantilla,
                motivo,
                mensaje
            )
            resultado['omitidas'].append({
                'bailarin_id': bailarin.id,
                'bailarin': nombre_completo,
                'tarjeta_id': tarjeta.id,
                'mensaje': (
                    f'PARA EL BAILARIN {nombre_completo} NO SE GENERO '
                    f'LA TARJETA POR LOS SIGUIENTES MOTIVOS: {motivo}.'
                ),
                'motivos': [motivo],
            })
            continue

        tarjeta.mensaje_generado = mensaje
        tarjeta.plantilla_utilizada = plantilla
        tarjeta.estado_generacion = (
            TarjetaCumpleanos.EstadoGeneracion.GENERADA
        )
        tarjeta.motivo_no_generacion = ''
        tarjeta.fecha_generacion = timezone.now()
        tarjeta.save()

        item = {
            'bailarin_id': bailarin.id,
            'bailarin': nombre_completo,
            'tarjeta_id': tarjeta.id,
            'imagen': tarjeta.imagen.url,
        }
        resultado['generadas'].append(item)

    if resultado['ya_existentes'] and not (
        resultado['generadas'] or resultado['omitidas']
    ):
        resultado['mensaje'] = (
            f'Las tarjetas de cumpleaños para el año {fecha.year} '
            'ya se encuentran realizadas.'
        )

    return resultado
