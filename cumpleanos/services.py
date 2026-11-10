from django.core.files.base import ContentFile
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from rest_framework.exceptions import APIException

from bailarines.models import Bailarin, Inscripcion
from .generador_afiches import generar_afiche
from .models import PlantillaCumpleanos, TarjetaCumpleanos


def _registrar_no_generada(bailarin, anio, plantilla, motivo):
    tarjeta, _ = TarjetaCumpleanos.objects.get_or_create(
        bailarin=bailarin,
        anio=anio
    )
    if tarjeta.imagen:
        return tarjeta

    tarjeta.estado_generacion = TarjetaCumpleanos.EstadoGeneracion.NO_GENERADA
    tarjeta.motivo_no_generacion = motivo
    tarjeta.plantilla_utilizada = plantilla
    tarjeta.save(update_fields=[
        'estado_generacion',
        'motivo_no_generacion',
        'plantilla_utilizada',
        'actualizado_en',
    ])
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
            _registrar_no_generada(
                bailarin,
                fecha.year,
                plantilla,
                texto_motivos
            )
            resultado['omitidas'].append({
                'bailarin_id': bailarin.id,
                'bailarin': nombre_completo,
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
            resultado['ya_existentes'].append({
                'bailarin_id': bailarin.id,
                'bailarin': nombre_completo,
                'tarjeta_id': tarjeta.id,
                'imagen': tarjeta.imagen.url,
            })
            continue

        contenido_afiche = None
        try:
            contenido_afiche = generar_afiche(bailarin, mensaje)
        except (APIException, OSError, ValueError) as error:
            motivo = (
                f'error al generar el afiche: '
                f'{getattr(error, "detail", error)}'
            )
            _registrar_no_generada(
                bailarin,
                fecha.year,
                plantilla,
                motivo
            )
            resultado['omitidas'].append({
                'bailarin_id': bailarin.id,
                'bailarin': nombre_completo,
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
        tarjeta.imagen.save(
            f'afiche_{bailarin.id}_{fecha.year}.jpeg',
            ContentFile(contenido_afiche),
            save=False
        )
        tarjeta.save()

        item = {
            'bailarin_id': bailarin.id,
            'bailarin': nombre_completo,
            'tarjeta_id': tarjeta.id,
            'imagen': tarjeta.imagen.url,
        }
        resultado['generadas'].append(item)

    return resultado
