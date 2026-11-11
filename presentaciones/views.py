from rest_framework import serializers
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.viewsets import GenericViewSet

from usuarios.permisos import PermisosPorModelo

from .models import Presentacion
from .serializers import PresentacionSerializer


class PresentacionFiltrosSerializer(serializers.Serializer):
    mes = serializers.IntegerField(min_value=1, max_value=12, required=False)
    anio = serializers.IntegerField(min_value=1, max_value=9999, required=False)
    lugar = serializers.CharField(required=False, allow_blank=False)


class PresentacionViewSet(
    CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin,
    GenericViewSet
):
    queryset = Presentacion.objects.select_related('persona_cargo').prefetch_related(
        'elencos', 'bitacora__coreografias'
    )
    serializer_class = PresentacionSerializer
    permission_classes = [PermisosPorModelo]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != 'list':
            return queryset
        filtros = PresentacionFiltrosSerializer(data=self.request.query_params.dict())
        filtros.is_valid(raise_exception=True)
        valores = filtros.validated_data
        if 'mes' in valores:
            queryset = queryset.filter(fecha__month=valores['mes'])
        if 'anio' in valores:
            queryset = queryset.filter(fecha__year=valores['anio'])
        if 'lugar' in valores:
            queryset = queryset.filter(lugar__icontains=valores['lugar'])
        return queryset
