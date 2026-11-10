
from django.conf import settings
from django.db import models


class PlantillaCumpleanos(models.Model):

    class Elenco(models.TextChoices):
        INFANTIL = 'INFANTIL', 'Infantil'
        PLANTA = 'PLANTA', 'Planta'
        MASTER = 'MÁSTER', 'Máster'

    elenco = models.CharField(
        max_length=30,
        choices=Elenco.choices,
        unique=True
    )

    mensaje = models.TextField()

    activa = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cumpleanos_plantillacumpleanos'
        verbose_name = 'Plantilla de cumpleaños'
        verbose_name_plural = 'Plantillas de cumpleaños'
        ordering = ['elenco']

    def __str__(self):
        return f'Plantilla de cumpleaños - {self.get_elenco_display()}'


class TarjetaCumpleanos(models.Model):

    class EstadoGeneracion(models.TextChoices):
        GENERADA = 'GENERADA', 'Afiche generado'
        NO_GENERADA = 'NO_GENERADA', 'Afiche no generado'

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de revisión'
        APROBADA = 'APROBADA', 'Aprobada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'

    bailarin = models.ForeignKey(
        'bailarines.Bailarin',
        on_delete=models.PROTECT,
        related_name='tarjetas_cumpleanos'
    )

    anio = models.PositiveSmallIntegerField()

    imagen = models.ImageField(
        upload_to='cumpleanos/tarjetas/',
        null=True,
        blank=True
    )

    mensaje_generado = models.TextField(blank=True)

    estado_generacion = models.CharField(
        max_length=15,
        choices=EstadoGeneracion.choices,
        default=EstadoGeneracion.NO_GENERADA
    )

    motivo_no_generacion = models.TextField(blank=True)

    plantilla_utilizada = models.ForeignKey(
        PlantillaCumpleanos,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tarjetas_generadas'
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )

    fecha_generacion = models.DateTimeField(
        null=True,
        blank=True
    )

    fecha_aprobacion = models.DateTimeField(
        null=True,
        blank=True
    )

    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tarjetas_cumpleanos_aprobadas'
    )

    fecha_rechazo = models.DateTimeField(
        null=True,
        blank=True
    )

    rechazado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tarjetas_cumpleanos_rechazadas'
    )

    motivo_rechazo = models.TextField(blank=True)

    observaciones = models.TextField(
        blank=True
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cumpleanos_tarjetacumpleanos'
        verbose_name = 'Tarjeta de cumpleaños'
        verbose_name_plural = 'Tarjetas de cumpleaños'
        ordering = ['-anio', 'bailarin__apellidos', 'bailarin__nombres']
        permissions = [
            (
                'aprobar_tarjetacumpleanos',
                'Puede aprobar o rechazar tarjetas de cumpleaños'
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['bailarin', 'anio'],
                name='unique_tarjeta_bailarin_anio'
            )
        ]

    def __str__(self):
        return f'{self.bailarin} - Cumpleaños {self.anio}'


class PublicacionRedSocial(models.Model):

    class Plataforma(models.TextChoices):
        FACEBOOK = 'FACEBOOK', 'Facebook'
        INSTAGRAM = 'INSTAGRAM', 'Instagram'

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PUBLICADA = 'PUBLICADA', 'Publicada'
        ERROR = 'ERROR', 'Error de publicación'

    tarjeta = models.ForeignKey(
        TarjetaCumpleanos,
        on_delete=models.PROTECT,
        related_name='publicaciones'
    )

    plataforma = models.CharField(
        max_length=15,
        choices=Plataforma.choices
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )

    texto_publicacion = models.TextField(
        blank=True
    )

    fecha_publicacion = models.DateTimeField(
        null=True,
        blank=True
    )

    id_publicacion_externa = models.CharField(
        max_length=255,
        blank=True
    )

    mensaje_error = models.TextField(
        blank=True
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cumpleanos_publicacionredsocial'
        verbose_name = 'Publicación en red social'
        verbose_name_plural = 'Publicaciones en redes sociales'
        ordering = ['-creado_en']
        constraints = [
            models.UniqueConstraint(
                fields=['tarjeta', 'plataforma'],
                name='unique_publicacion_tarjeta_plataforma'
            )
        ]

    def __str__(self):
        return (
            f'{self.tarjeta} - '
            f'{self.get_plataforma_display()}'
        )
