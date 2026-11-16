from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.viewsets import ModelViewSet

from .models import Parametro
from .serializers import ParametroSerializer


class EsAdministrador(BasePermission):

    """Lectura para cualquier usuario autenticado; escritura solo Administrador."""

    def has_permission(self, request, view):
        usuario = request.user
        if not (usuario and usuario.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return (
            usuario.is_superuser
            or usuario.groups.filter(name='Administrador').exists()
        )


class ParametroViewSet(ModelViewSet):
    queryset = Parametro.objects.all()
    serializer_class = ParametroSerializer
    permission_classes = [EsAdministrador]

    @action(
        detail=False,
        methods=['get'],
        url_path=r'por-nombre/(?P<nombre>[^/]+)'
    )
    def por_nombre(self, request, nombre=None):
        parametro = get_object_or_404(Parametro, nombre=nombre)
        return Response(self.get_serializer(parametro).data)
