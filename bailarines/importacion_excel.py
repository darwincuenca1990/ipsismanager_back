import re
import unicodedata
from datetime import date, datetime
from zipfile import BadZipFile

from django.db import transaction
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from rest_framework.exceptions import ValidationError

from .models import Bailarin, Inscripcion
from .serializers import BailarinSerializer, GrupoFamiliarSerializer


def _normalizar(valor):
    texto = unicodedata.normalize('NFKD', str(valor).strip().lower())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', texto).strip()


ENCABEZADOS = {
    'cedula de identidad': 'cedula',
    'cedula': 'cedula',
    'apellidos': 'apellidos',
    'nombres': 'nombres',
    'genero': 'genero',
    'fecha de nacimiento': 'fecha_nacimiento',
    'elenco': 'elenco',
    'lugar de nacimiento': 'lugar_nacimiento',
    'celular': 'celular',
    'correo electronico': 'correo',
    'correo': 'correo',
    'convive': 'vive_con',
    'convive con': 'vive_con',
    'vive con': 'vive_con',
    'direccion domiciliaria': 'direccion_domicilio',
    'direccion domicilio': 'direccion_domicilio',
    'referebcua domiciliaria': 'referencia_domicilio',
    'referencia domiciliaria': 'referencia_domicilio',
    'referencia domicilio': 'referencia_domicilio',
    'situacion actual': 'situacion_actual',
    'institucion educativa': 'institucion_estudio',
    'institucion estudio': 'institucion_estudio',
    'lugar de trabajo': 'lugar_trabajo',
    'padece enfermedad': 'padece_enfermedad',
    'detalle de enfermedad': 'detalle_enfermedad',
    'detalle enfermedad': 'detalle_enfermedad',
    'fecha de ingreso a la agrupacion': 'fecha_ingreso_agrupacion',
    'fecha ingreso agrupacion': 'fecha_ingreso_agrupacion',
    'motivo de ingreso': 'motivo_ingreso_agrupacion',
    'motivo ingreso agrupacion': 'motivo_ingreso_agrupacion',
    'estado': 'estado',
    'fecha salida': 'fecha_salida',
    'apellidos del padre': 'apellidos_papa',
    'apellidos papa': 'apellidos_papa',
    'nombres del padre': 'nombres_papa',
    'nombres papa': 'nombres_papa',
    'celular del padre': 'celular_papa',
    'celular papa': 'celular_papa',
    'trabajo del padre': 'lugar_trabajo_papa',
    'lugar trabajo papa': 'lugar_trabajo_papa',
    'apellidos de la madre': 'apellidos_mama',
    'apellidos mama': 'apellidos_mama',
    'nombres de la madre': 'nombres_mama',
    'nombres mama': 'nombres_mama',
    'celular de la madre': 'celular_mama',
    'celular mama': 'celular_mama',
    'trabajo de la madre': 'lugar_trabajo_mama',
    'lugar trabajo mama': 'lugar_trabajo_mama',
    'quien sera el representante': 'representante',
    'representante': 'representante',
}

FAMILIA = (
    'apellidos_papa', 'nombres_papa', 'celular_papa', 'lugar_trabajo_papa',
    'apellidos_mama', 'nombres_mama', 'celular_mama', 'lugar_trabajo_mama',
)
INSCRIPCION = (
    'fecha_ingreso_agrupacion', 'estado', 'motivo_ingreso_agrupacion',
    'fecha_salida',
)
REQUERIDOS = (
    'cedula', 'apellidos', 'nombres', 'fecha_nacimiento', 'elenco',
    'fecha_ingreso_agrupacion', 'estado', 'representante',
)


def _texto_celda(celda):
    valor = celda.value
    if valor is None:
        return None
    if isinstance(valor, (date, datetime)):
        return valor.date().isoformat() if isinstance(valor, datetime) else valor.isoformat()
    if isinstance(valor, int) and not isinstance(valor, bool):
        formato = celda.number_format
        if re.fullmatch(r'0+', formato):
            return str(valor).zfill(len(formato))
    return str(valor).strip()


def _opcion(valor, opciones, campo):
    if not valor:
        return None
    valores = {_normalizar(opcion): opcion for opcion, _ in opciones}
    resultado = valores.get(_normalizar(valor))
    if resultado is None:
        raise ValidationError({campo: f'Valor no válido: {valor}.'})
    return resultado


def _fecha(valor):
    if not valor:
        return valor
    for formato in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(valor, formato).date().isoformat()
        except ValueError:
            continue
    return valor


def _crear_fila(datos):
    representante = _normalizar(datos.pop('representante', '') or '')
    if representante not in ('padre', 'madre'):
        raise ValidationError({'representante': 'Indique Padre o Madre.'})
    sufijo = 'papa' if representante == 'padre' else 'mama'
    nombres = datos.get(f'nombres_{sufijo}') or ''
    apellidos = datos.get(f'apellidos_{sufijo}') or ''
    familia = {campo: datos.pop(campo) for campo in FAMILIA if datos.get(campo)}
    familia.update({
        'nombres_completos_representante': f'{nombres} {apellidos}'.strip(),
        'celular_representante': familia.get(f'celular_{sufijo}', ''),
        'lugar_trabajo_representante': familia.get(f'lugar_trabajo_{sufijo}', ''),
        'parentesco': representante.capitalize(),
    })
    if not nombres or not apellidos:
        raise ValidationError({
            'representante': 'El representante debe tener nombres y apellidos.'
        })

    situacion = _normalizar(datos.pop('situacion_actual', '') or '')
    if situacion not in ('', 'estudia', 'trabaja'):
        raise ValidationError({'situacion_actual': 'Indique Estudia o Trabaja.'})
    datos['estudia'] = situacion == 'estudia'
    datos['trabaja'] = situacion == 'trabaja'

    enfermedad = _normalizar(datos.pop('padece_enfermedad', '') or '')
    if enfermedad not in ('', 'si', 'no', 'true', 'false', '1', '0'):
        raise ValidationError({'padece_enfermedad': 'Indique Sí o No.'})
    datos['padece_enfermedad'] = enfermedad in ('si', 'true', '1')

    for campo, opciones in (
        ('elenco', Bailarin.Elenco.choices),
        ('genero', Bailarin.Genero.choices),
        ('vive_con', Bailarin.ViveCon.choices),
        ('estado', Inscripcion.Estado.choices),
    ):
        if datos.get(campo):
            datos[campo] = _opcion(datos[campo], opciones, campo)
    for campo in ('fecha_nacimiento', 'fecha_ingreso_agrupacion', 'fecha_salida'):
        if datos.get(campo):
            datos[campo] = _fecha(datos[campo])

    inscripcion = {
        campo: datos.pop(campo) for campo in INSCRIPCION if datos.get(campo)
    }
    datos = {campo: valor for campo, valor in datos.items() if valor not in (None, '')}
    datos['inscripcion'] = inscripcion

    with transaction.atomic():
        familia_serializer = GrupoFamiliarSerializer(data=familia)
        familia_serializer.is_valid(raise_exception=True)
        grupo = familia_serializer.save()
        datos['grupo_familiar_id'] = grupo.pk
        serializer = BailarinSerializer(data=datos)
        serializer.is_valid(raise_exception=True)
        bailarin = serializer.save()
    return bailarin.pk


def importar_bailarines_excel(archivo):
    try:
        libro = load_workbook(archivo, read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, OSError, ValueError, KeyError) as error:
        raise ValidationError({'archivo': 'El archivo no es un Excel .xlsx válido.'}) from error

    try:
        hoja = libro.worksheets[0]
        encabezados = next(hoja.iter_rows(min_row=2, max_row=2), ())
        columnas = {}
        for indice, celda in enumerate(encabezados):
            if celda.value is None:
                continue
            campo = ENCABEZADOS.get(_normalizar(celda.value))
            if campo:
                if campo in columnas:
                    raise ValidationError({'archivo': f'Columna duplicada: {campo}.'})
                columnas[campo] = indice
        faltantes = [campo for campo in REQUERIDOS if campo not in columnas]
        if faltantes:
            raise ValidationError({
                'archivo': 'Faltan columnas obligatorias en la fila 2: ' + ', '.join(faltantes)
            })

        creados, errores = [], []
        for numero, fila in enumerate(hoja.iter_rows(min_row=3), start=3):
            datos = {
                campo: _texto_celda(fila[indice])
                for campo, indice in columnas.items()
            }
            if not any(datos.values()):
                continue
            try:
                pk = _crear_fila(datos)
            except ValidationError as error:
                errores.append({'fila': numero, 'errores': error.detail})
            else:
                creados.append({'fila': numero, 'id': pk})
        return {'creados': creados, 'errores': errores}
    finally:
        libro.close()
