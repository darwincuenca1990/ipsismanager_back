from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from dotenv import dotenv_values

from parametros.models import Parametro


ARCHIVOS = ('_facebook.env', '_googedrive.env')


class Command(BaseCommand):

    help = (
        'Importa a la tabla de parámetros las variables de _facebook.env '
        'y _googedrive.env (crea o actualiza por nombre).'
    )

    def handle(self, *args, **kwargs):
        for archivo in ARCHIVOS:
            ruta = Path(settings.BASE_DIR) / archivo
            if not ruta.is_file():
                self.stdout.write(f'{archivo}: no existe, se omite.')
                continue
            for nombre, valor in dotenv_values(ruta).items():
                if valor is None:
                    continue
                _, creado = Parametro.objects.update_or_create(
                    nombre=nombre,
                    defaults={
                        'valor': valor,
                        'estado': Parametro.Estado.ACTIVO,
                    }
                )
                self.stdout.write(
                    f'{nombre}: {"creado" if creado else "actualizado"}'
                )
