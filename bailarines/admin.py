
from django.contrib import admin
from .models import Bailarin, GrupoFamiliar, Inscripcion


@admin.register(GrupoFamiliar)
class GrupoFamiliarAdmin(admin.ModelAdmin):
    list_display = (
        'nombres_completos_representante',
        'celular_representante',
        'parentesco',
    )
    search_fields = (
        'nombres_completos_representante',
        'apellidos_papa',
        'apellidos_mama',
        'celular_representante',
    )


@admin.register(Bailarin)
class BailarinAdmin(admin.ModelAdmin):
    list_display = (
        'cedula',
        'apellidos',
        'nombres',
        'elenco',
        'fecha_nacimiento',
    )
    list_filter = ('elenco',)
    search_fields = (
        'cedula',
        'apellidos',
        'nombres',
    )


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = (
        'bailarin',
        'fecha_ingreso_agrupacion',
        'estado',
        'fecha_salida',
    )
    list_filter = ('estado',)
    search_fields = (
        'bailarin__cedula',
        'bailarin__apellidos',
        'bailarin__nombres',
    )
