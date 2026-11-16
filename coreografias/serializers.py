from rest_framework import serializers

from .models import Coreografia


class CoreografiaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Coreografia
        fields = ['id', 'nombre', 'region', 'descripcion', 'url_video']
        read_only_fields = ['id']
