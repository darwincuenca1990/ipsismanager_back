from django.db import models


class GrupoFamiliar(models.Model):

    apellidos_papa = models.CharField(
        max_length=150,
        blank=True
    )
    nombres_papa = models.CharField(
        max_length=150,
        blank=True
    )
    celular_papa = models.CharField(
        max_length=20,
        blank=True
    )
    lugar_trabajo_papa = models.CharField(
        max_length=200,
        blank=True
    )

    apellidos_mama = models.CharField(
        max_length=150,
        blank=True
    )
    nombres_mama = models.CharField(
        max_length=150,
        blank=True
    )
    celular_mama = models.CharField(
        max_length=20,
        blank=True
    )
    lugar_trabajo_mama = models.CharField(
        max_length=200,
        blank=True
    )

    nombres_completos_representante = models.CharField(
        max_length=200
    )
    lugar_trabajo_representante = models.CharField(
        max_length=200,
        blank=True
    )
    celular_representante = models.CharField(
        max_length=20
    )
    parentesco = models.CharField(
        max_length=100
    )

    class Meta:
        db_table = 'bailarines_grupofamiliar'
        verbose_name = 'Grupo familiar'
        verbose_name_plural = 'Grupos familiares'

    def __str__(self):
        return self.nombres_completos_representante


class Bailarin(models.Model):

    class Genero(models.TextChoices):
        MASCULINO = 'MASCULINO', 'Masculino'
        FEMENINO = 'FEMENINO', 'Femenino'

    class ViveCon(models.TextChoices):
        PADRES = 'PADRES', 'Padres'
        FAMILIARES = 'FAMILIARES', 'Familiares'
        OTROS = 'OTROS', 'Otros'

    class Elenco(models.TextChoices):
        INFANTIL = 'INFANTIL', 'Infantil'
        PLANTA = 'PLANTA', 'Planta'
        MASTER = 'MÁSTER', 'Máster'
        ASPIRANTE_INFANTIL = 'ASPIRANTE INFANTIL', 'Aspirante infantil'
        ASPIRANTE_PLANTA = 'ASPIRANTE PLANTA', 'Aspirante planta'
        ASPIRANTE_MASTER = 'ASPIRANTE MÁSTER', 'Aspirante máster'

    grupo_familiar = models.ForeignKey(
        GrupoFamiliar,
        on_delete=models.PROTECT,
        related_name='bailarines'
    )

    elenco = models.CharField(
        max_length=30,
        choices=Elenco.choices
    )

    cedula = models.CharField(
        max_length=20,
        unique=True
    )
    apellidos = models.CharField(max_length=150)
    nombres = models.CharField(max_length=150)
    genero = models.CharField(
        max_length=9,
        choices=Genero.choices,
        null=True,
        blank=True
    )

    estudia = models.BooleanField(default=False)
    institucion_estudio = models.CharField(
        max_length=200,
        blank=True
    )

    trabaja = models.BooleanField(default=False)
    lugar_trabajo = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    direccion_domicilio = models.CharField(
        max_length=250,
        blank=True
    )
    referencia_domicilio = models.CharField(
        max_length=250,
        blank=True
    )

    vive_con = models.CharField(
        max_length=20,
        choices=ViveCon.choices,
        blank=True
    )

    fecha_nacimiento = models.DateField()
    lugar_nacimiento = models.CharField(
        max_length=150,
        blank=True
    )

    celular = models.CharField(
        max_length=20,
        blank=True
    )
    padece_enfermedad = models.BooleanField(default=False)
    detalle_enfermedad = models.TextField(
        null=True,
        blank=True
    )

    correo = models.EmailField(blank=True)

    fotografia = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    fotografia_drive_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    autorizado_publicacion = models.BooleanField(
        default=False
    )

    fecha_autorizacion_publicacion = models.DateField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'bailarines_bailarin'
        verbose_name = 'Bailarín'
        verbose_name_plural = 'Bailarines'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f'{self.apellidos} {self.nombres}'


class Inscripcion(models.Model):

    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        INACTIVO = 'INACTIVO', 'Inactivo'

    bailarin = models.ForeignKey(
        Bailarin,
        on_delete=models.PROTECT,
        related_name='inscripciones'
    )

    fecha_ingreso_agrupacion = models.DateField()

    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVO
    )

    motivo_ingreso_agrupacion = models.TextField(
        blank=True
    )

    fecha_salida = models.DateField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'bailarines_inscripcion'
        verbose_name = 'Inscripción'
        verbose_name_plural = 'Inscripciones'
        ordering = ['-fecha_ingreso_agrupacion']

    def __str__(self):
        return (
            f'{self.bailarin} - '
            f'{self.get_estado_display()}'
        )
