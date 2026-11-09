from django.core.files.base import ContentFile
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from bailarines.models import Bailarin, Inscripcion
from .generador_afiches import generar_afiche
from .models import PlantillaCumpleanos, TarjetaCumpleanos


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
            resultado['omitidas'].append({
                'bailarin_id': bailarin.id,
                'bailarin': nombre_completo,
                'mensaje': (
                    f'PARA EL BAILARIN {nombre_completo} NO SE GENERO '
                    f'LA TARJETA POR LOS SIGUIENTES MOTIVOS: '
                    f'{"; ".join(motivos)}.'
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
                'fecha_generacion': timezone.now(),
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

        contenido_afiche = generar_afiche(bailarin, mensaje)
        tarjeta.mensaje_generado = mensaje
        tarjeta.plantilla_utilizada = plantilla
        tarjeta.fecha_generacion = tarjeta.fecha_generacion or timezone.now()
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
