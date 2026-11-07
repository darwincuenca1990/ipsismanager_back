from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):

    class Meta:
        db_table = 'usuarios_usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.username