from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook
from rest_framework.test import APIClient

from .importacion_excel import importar_bailarines_excel
from .models import Bailarin, GrupoFamiliar, Inscripcion


ENCABEZADOS = [
    'Nro', 'Cédula de Identidad', 'Apellidos', 'Nombres', 'GENERO',
    'Fecha de Nacimiento', 'ELENCO', 'Lugar de Nacimiento', 'CELULAR',
    'Correo Eléctronico', 'Convive', 'Direccion Domiciliaria',
    'Referebcua Domiciliaria', 'Situacion Actual', 'Institución Educativa',
    'Lugar de Trabajo', 'Padece Enfermedad', 'Detalle de Enfermedad',
    'Fecha de Ingreso a la Agrupación', 'Motivo de Ingreso', 'Estado',
    'Apellidos del Padre', 'Nombres del Padre', 'Celular del Padre',
    'Trabajo del Padre', 'Apellidos de la Madre', 'Nombres de la Madre',
    'Celular de la Madre', 'Trabajo de la Madre', 'Quien sera el Representante',
]


def fila(cedula='0123456789'):
    return [
        1, cedula, 'Pérez', 'Ana', 'Femenino', date(2000, 3, 10),
        'Máster', 'Quito', '0999999999', 'ana@example.com', 'Padres',
        'Calle', 'Parque', 'Estudia', 'Colegio', '', 'No', '',
        date(2024, 1, 1), 'Danza', 'Activo', 'Pérez', 'Juan',
        '0988888888', 'Oficina', 'López', 'María', '0977777777',
        'Escuela', 'Madre',
    ]


def excel(*filas, encabezados=ENCABEZADOS):
    libro = Workbook()
    hoja = libro.active
    hoja.append(['Plantilla'])
    hoja.append(encabezados)
    for valores in filas:
        hoja.append(valores)
    contenido = BytesIO()
    libro.save(contenido)
    contenido.seek(0)
    return contenido


class ImportacionExcelTests(TestCase):
    def test_crea_bailarin_inscripcion_y_representante(self):
        resultado = importar_bailarines_excel(excel(fila()))
        self.assertEqual(len(resultado['creados']), 1)
        self.assertEqual(resultado['errores'], [])
        bailarin = Bailarin.objects.get()
        self.assertEqual(bailarin.cedula, '0123456789')
        self.assertEqual(bailarin.elenco, Bailarin.Elenco.MASTER)
        self.assertTrue(bailarin.estudia)
        self.assertFalse(bailarin.trabaja)
        self.assertFalse(bailarin.autorizado_publicacion)
        self.assertEqual(bailarin.grupo_familiar.nombres_completos_representante, 'María López')
        self.assertEqual(bailarin.grupo_familiar.celular_representante, '0977777777')
        self.assertEqual(bailarin.inscripciones.get().estado, Inscripcion.Estado.ACTIVO)

    def test_errores_no_impiden_crear_filas_validas_y_no_dejan_grupos_huerfanos(self):
        invalida = fila('9876543210')
        invalida[14] = ''
        resultado = importar_bailarines_excel(excel(fila(), invalida, fila()))
        self.assertEqual([x['fila'] for x in resultado['creados']], [3])
        self.assertEqual([x['fila'] for x in resultado['errores']], [4, 5])
        self.assertIn('institucion_estudio', resultado['errores'][0]['errores'])
        self.assertIn('cedula', resultado['errores'][1]['errores'])
        self.assertEqual(GrupoFamiliar.objects.count(), 1)
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_formato_cedula_numerica_con_ceros(self):
        libro = Workbook()
        hoja = libro.active
        hoja.append(['Plantilla'])
        hoja.append(ENCABEZADOS)
        valores = fila()
        valores[1] = 123456789
        hoja.append(valores)
        hoja['B3'].number_format = '0000000000'
        archivo = BytesIO()
        libro.save(archivo)
        archivo.seek(0)
        importar_bailarines_excel(archivo)
        self.assertEqual(Bailarin.objects.get().cedula, '0123456789')

    def test_rechaza_encabezados_incompletos_y_representante_invalido(self):
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            importar_bailarines_excel(excel(fila(), encabezados=['Nro']))
        datos = fila()
        datos[-1] = 'Otro'
        resultado = importar_bailarines_excel(excel(datos))
        self.assertIn('representante', resultado['errores'][0]['errores'])
        self.assertFalse(GrupoFamiliar.objects.exists())

    def test_endpoint_exige_permiso_de_creacion(self):
        usuario = get_user_model().objects.create_user(username='prueba')
        cliente = APIClient()
        cliente.force_authenticate(usuario)
        def archivo():
            return SimpleUploadedFile(
                'bailarines.xlsx', excel(fila()).getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
        url = '/api/bailarines/importar-excel/'
        self.assertEqual(cliente.post(url, {'archivo': archivo()}).status_code, 403)
        usuario.user_permissions.add(Permission.objects.get(
            content_type__app_label='bailarines', codename='add_bailarin'
        ))
        usuario = get_user_model().objects.get(pk=usuario.pk)
        cliente.force_authenticate(usuario)
        respuesta = cliente.post(url, {'archivo': archivo()})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data['creados']), 1)

    def test_archivo_invalido(self):
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            importar_bailarines_excel(BytesIO(b'no es excel'))
