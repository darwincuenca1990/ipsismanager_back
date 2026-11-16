from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Estado(models.TextChoices):
    ACTIVO = 'ACTIVO', 'Activo'
    INACTIVO = 'INACTIVO', 'Inactivo'


class TipoTraje(models.Model):
    nombre = models.CharField(max_length=150)
    variante = models.CharField(max_length=100)
    region_cultura = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    fotografia_referencia = models.ImageField(
        upload_to='trajes/tipos/', blank=True, null=True
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre', 'id']

    def __str__(self):
        return f'{self.nombre} - {self.variante}'


class PrendaTraje(models.Model):
    nombre_prenda = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    fotografia = models.ImageField(upload_to='trajes/prendas/', blank=True, null=True)
    observaciones = models.TextField(blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
    tipos_traje = models.ManyToManyField(
        TipoTraje, through='ComposicionTraje', related_name='prendas'
    )

    class Meta:
        ordering = ['nombre_prenda', 'id']

    def __str__(self):
        return self.nombre_prenda


class ComposicionTraje(models.Model):
    tipo_traje = models.ForeignKey(
        TipoTraje, on_delete=models.PROTECT, related_name='composicion'
    )
    prenda = models.ForeignKey(
        PrendaTraje, on_delete=models.PROTECT, related_name='composiciones'
    )
    cantidad_requerida = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))]
    )
    observaciones = models.TextField(blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['tipo_traje', 'prenda'], name='trajes_composicion_unica'),
            models.CheckConstraint(condition=Q(cantidad_requerida__gte=1), name='trajes_cantidad_prenda_positiva'),
            models.CheckConstraint(
                condition=Q(precio_unitario__isnull=True) | Q(precio_unitario__gte=0),
                name='trajes_precio_prenda_no_negativo',
            ),
        ]


class AdquisicionTraje(models.Model):
    tipo_traje = models.ForeignKey(
        TipoTraje, on_delete=models.PROTECT, related_name='adquisiciones'
    )
    fecha_adquisicion = models.DateField()
    cantidad_adquirida = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    costo_unitario = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))]
    )
    costo_total = models.DecimalField(max_digits=22, decimal_places=2, editable=False)
    proveedor = models.CharField(max_length=200, blank=True)
    observaciones = models.TextField(blank=True)
    comprobante = models.FileField(upload_to='trajes/comprobantes/', blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_adquisicion', '-id']
        constraints = [
            models.CheckConstraint(condition=Q(cantidad_adquirida__gte=1), name='trajes_cantidad_compra_positiva'),
            models.CheckConstraint(condition=Q(costo_unitario__gte=0), name='trajes_costo_unitario_no_negativo'),
        ]

    def save(self, *args, **kwargs):
        self.costo_total = self.cantidad_adquirida * self.costo_unitario
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {'costo_total'}
        super().save(*args, **kwargs)
