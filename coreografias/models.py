from django.db import models


class Coreografia(models.Model):
    nombre = models.CharField(max_length=150)
    region = models.CharField(max_length=150)
    descripcion = models.TextField()
    url_video = models.URLField(max_length=500)

    class Meta:
        db_table = 'coreografias_coreografia'
        verbose_name = 'Coreografía'
        verbose_name_plural = 'Coreografías'
        ordering = ['nombre', 'id']

    def __str__(self):
        return self.nombre
