from django.db import models


class Parametro(models.Model):

    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        INACTIVO = 'INACTIVO', 'Inactivo'

    nombre = models.CharField(max_length=150, unique=True)
    valor = models.TextField()
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVO
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'parametros_parametro'
        verbose_name = 'Parámetro'
        verbose_name_plural = 'Parámetros'
        ordering = ['nombre', 'id']

    def __str__(self):
        return self.nombre
