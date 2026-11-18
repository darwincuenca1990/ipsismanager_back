from django.contrib import admin

from .models import AdquisicionTraje, ComposicionTraje, PrendaTraje, TipoTraje


@admin.register(TipoTraje)
class TipoTrajeAdmin(admin.ModelAdmin):
    list_display = (
        'nombre',
        'variante',
        'region_cultura',
        'estado',
        'fecha_actualizacion',
    )
    list_filter = ('estado', 'region_cultura')
    search_fields = ('nombre', 'variante', 'region_cultura', 'descripcion')


@admin.register(PrendaTraje)
class PrendaTrajeAdmin(admin.ModelAdmin):
    list_display = ('nombre_prenda', 'estado')
    list_filter = ('estado',)
    search_fields = ('nombre_prenda', 'descripcion', 'observaciones')


@admin.register(ComposicionTraje)
class ComposicionTrajeAdmin(admin.ModelAdmin):
    list_display = (
        'tipo_traje',
        'prenda',
        'cantidad_requerida',
        'precio_unitario',
        'estado',
    )
    list_filter = ('estado', 'tipo_traje')
    search_fields = ('tipo_traje__nombre', 'tipo_traje__variante', 'prenda__nombre_prenda')


@admin.register(AdquisicionTraje)
class AdquisicionTrajeAdmin(admin.ModelAdmin):
    list_display = (
        'tipo_traje',
        'fecha_adquisicion',
        'cantidad_adquirida',
        'costo_unitario',
        'costo_total',
        'proveedor',
    )
    list_filter = ('fecha_adquisicion', 'tipo_traje')
    search_fields = ('tipo_traje__nombre', 'tipo_traje__variante', 'proveedor')
    readonly_fields = ('costo_total', 'fecha_registro')
