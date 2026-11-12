from datetime import date
from decimal import Decimal

from .models import Presentacion


def resumen_vacio(anio):
    return {
        'anio': anio,
        'cantidad_presentaciones': 0,
        'ids_presentaciones': [],
        'costo_total_presentacion': Decimal('0.00'),
        'costo_transporte': Decimal('0.00'),
        'costo_neto': Decimal('0.00'),
    }


def resumenes_por_mes(anio, ultimo_mes, primer_mes=1):
    resumenes = {
        (periodo, mes): resumen_vacio(periodo)
        for periodo in (anio - 1, anio)
        for mes in range(primer_mes, ultimo_mes + 1)
    }
    registros = Presentacion.objects.filter(
        fecha__gte=date(anio - 1, 1, 1),
        fecha__lte=date(anio, 12, 31),
        fecha__month__gte=primer_mes,
        fecha__month__lte=ultimo_mes,
    ).order_by('fecha', 'id').values_list(
        'id', 'fecha', 'costo_total_presentacion', 'costo_transporte'
    ).iterator()
    for pk, fecha, bruto, transporte in registros:
        resumen = resumenes.get((fecha.year, fecha.month))
        if resumen is None:
            continue
        resumen['cantidad_presentaciones'] += 1
        resumen['ids_presentaciones'].append(pk)
        resumen['costo_total_presentacion'] += bruto
        resumen['costo_transporte'] += transporte
        resumen['costo_neto'] += bruto - transporte
    for resumen in resumenes.values():
        for campo in ('costo_total_presentacion', 'costo_transporte', 'costo_neto'):
            resumen[campo] = format(resumen[campo], '.2f')
    return resumenes
