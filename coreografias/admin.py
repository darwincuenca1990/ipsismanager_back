from django.contrib import admin

from .models import Coreografia


@admin.register(Coreografia)
class CoreografiaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'region', 'url_video')
    search_fields = ('nombre', 'region')
