
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from bailarines.models import Bailarin, GrupoFamiliar, Inscripcion


class Command(BaseCommand):

    help = 'Configura los roles y permisos de IPSIS Manager'

    def handle(self, *args, **kwargs):

        # Crear los grupos
        administrador, _ = Group.objects.get_or_create(
            name='Administrador'
        )

        direccion, _ = Group.objects.get_or_create(
            name='Dirección'
        )

        # Administrador: todos los permisos del sistema
        administrador.permissions.set(
            Permission.objects.all()
        )

        # Dirección: permisos sobre los modelos de bailarines
        modelos = [
            Bailarin,
            GrupoFamiliar,
            Inscripcion,
        ]

        permisos_direccion = []

        for modelo in modelos:

            content_type = ContentType.objects.get_for_model(
                modelo
            )

            permisos = Permission.objects.filter(
                content_type=content_type,
                codename__in=[
                    f'add_{modelo._meta.model_name}',
                    f'view_{modelo._meta.model_name}',
                    f'change_{modelo._meta.model_name}',
                ]
            )

            permisos_direccion.extend(permisos)

        direccion.permissions.set(permisos_direccion)

        self.stdout.write(
            self.style.SUCCESS(
                'Roles y permisos configurados correctamente.'
            )
        )
