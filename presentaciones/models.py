from django.core.validators import MinValueValidator
from django.db import models

from bailarines.models import Bailarin
from coreografias.models import Coreografia


class Presentacion(models.Model):

    class Tipo(models.TextChoices):
        UN_ELENCO = 'UN ELENCO', 'Un elenco'
        FESTIVALIPSIS = 'FESTIVALIPSIS', 'Festival Ipsis'

    fecha = models.DateField()
    lugar = models.CharField(max_length=250)
    hora_presentacion = models.TimeField()
    persona_cargo = models.ForeignKey(
        Bailarin, on_delete=models.PROTECT, related_name='presentaciones_a_cargo'
    )
    costo_total_presentacion = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    costo_transporte = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    nombre_transporte = models.CharField(max_length=200)
    tipo_presentacion = models.CharField(max_length=20, choices=Tipo.choices)

    class Meta:
        db_table = 'presentaciones_presentacion'
        verbose_name = 'Presentación'
        verbose_name_plural = 'Presentaciones'
        ordering = ['-fecha', 'hora_presentacion', 'id']

    @property
    def costo_neto(self):
        return self.costo_total_presentacion - self.costo_transporte

    def __str__(self):
        return f'{self.fecha} - {self.lugar}'


class PresentacionElenco(models.Model):
    presentacion = models.ForeignKey(
        Presentacion, on_delete=models.CASCADE, related_name='elencos'
    )
    elenco = models.CharField(max_length=30, choices=Bailarin.Elenco.choices)

    class Meta:
        db_table = 'presentaciones_presentacionelenco'
        constraints = [
            models.UniqueConstraint(
                fields=['presentacion', 'elenco'], name='presentacion_elenco_unico'
            )
        ]


class Bitacora(models.Model):
    presentacion = models.ForeignKey(
        Presentacion, on_delete=models.CASCADE, related_name='bitacora'
    )
    bailarin = models.ForeignKey(
        Bailarin, on_delete=models.PROTECT, related_name='bitacoras_presentaciones'
    )
    coreografias = models.ManyToManyField(
        Coreografia, through='BitacoraCoreografia', related_name='bitacoras'
    )

    class Meta:
        db_table = 'presentaciones_bitacora'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['presentacion', 'bailarin'], name='presentacion_bailarin_unico'
            )
        ]


class BitacoraCoreografia(models.Model):
    bitacora = models.ForeignKey(Bitacora, on_delete=models.CASCADE)
    coreografia = models.ForeignKey(Coreografia, on_delete=models.PROTECT)

    class Meta:
        db_table = 'presentaciones_bitacoracoreografia'
        constraints = [
            models.UniqueConstraint(
                fields=['bitacora', 'coreografia'], name='bitacora_coreografia_unica'
            )
        ]
