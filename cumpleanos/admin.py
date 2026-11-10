
from django.contrib import admin
from .models import TarjetaCumpleanos, PublicacionRedSocial


class PublicacionRedSocialInline(admin.TabularInline):
    model = PublicacionRedSocial
    extra = 0
    fields = (
        'plataforma',
        'estado',
        'fecha_publicacion',
        'id_publicacion_externa',
    )
    readonly_fields = (
        'fecha_publicacion',
    )


@admin.register(TarjetaCumpleanos)
class TarjetaCumpleanosAdmin(admin.ModelAdmin):

    list_display = (
        'bailarin',
        'anio',
        'estado_generacion',
        'estado',
        'fecha_generacion',
        'fecha_aprobacion',
        'aprobado_por',
        'fecha_rechazo',
        'rechazado_por',
    )

    list_filter = (
        'anio',
        'estado_generacion',
        'estado',
    )

    search_fields = (
        'bailarin__nombres',
        'bailarin__apellidos',
        'bailarin__cedula',
    )

    readonly_fields = (
        'fecha_generacion',
        'fecha_aprobacion',
        'fecha_rechazo',
        'creado_en',
        'actualizado_en',
    )

    inlines = [PublicacionRedSocialInline]


@admin.register(PublicacionRedSocial)
class PublicacionRedSocialAdmin(admin.ModelAdmin):

    list_display = (
        'tarjeta',
        'plataforma',
        'estado',
        'fecha_publicacion',
    )

    list_filter = (
        'plataforma',
        'estado',
    )

    search_fields = (
        'tarjeta__bailarin__nombres',
        'tarjeta__bailarin__apellidos',
        'tarjeta__bailarin__cedula',
        'id_publicacion_externa',
    )

    readonly_fields = (
        'fecha_publicacion',
        'creado_en',
        'actualizado_en',
    )
