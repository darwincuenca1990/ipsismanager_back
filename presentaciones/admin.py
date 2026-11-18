from django.contrib import admin

from .models import Bitacora, BitacoraCoreografia, Presentacion, PresentacionElenco


@admin.register(Presentacion)
class PresentacionAdmin(admin.ModelAdmin):
    list_display = (
        'fecha',
        'lugar',
        'hora_presentacion',
        'clase_presentacion',
        'tipo_presentacion',
        'persona_cargo',
    )
    list_filter = ('tipo_presentacion', 'clase_presentacion', 'fecha')
    search_fields = (
        'lugar',
        'clase_presentacion',
        'persona_cargo__cedula',
        'persona_cargo__apellidos',
        'persona_cargo__nombres',
    )


@admin.register(PresentacionElenco)
class PresentacionElencoAdmin(admin.ModelAdmin):
    list_display = ('presentacion', 'elenco')
    list_filter = ('elenco',)
    search_fields = ('presentacion__lugar', 'presentacion__clase_presentacion')


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = ('presentacion', 'bailarin')
    search_fields = (
        'presentacion__lugar',
        'presentacion__clase_presentacion',
        'bailarin__cedula',
        'bailarin__apellidos',
        'bailarin__nombres',
    )


@admin.register(BitacoraCoreografia)
class BitacoraCoreografiaAdmin(admin.ModelAdmin):
    list_display = ('bitacora', 'coreografia')
    search_fields = (
        'bitacora__presentacion__lugar',
        'bitacora__bailarin__cedula',
        'coreografia__nombre',
    )
