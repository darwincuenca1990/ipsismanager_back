from django.contrib import admin

from .models import Parametro


@admin.register(Parametro)
class ParametroAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'valor', 'estado', 'fecha_registro')
    list_filter = ('estado',)
    search_fields = ('nombre',)
    readonly_fields = ('fecha_registro',)
