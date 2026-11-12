from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from usuarios.permisos import PermisosPorModelo

from .models import Presentacion
from .reportes import resumenes_por_mes
from .serializers import PresentacionSerializer


class PresentacionFiltrosSerializer(serializers.Serializer):
    mes = serializers.IntegerField(min_value=1, max_value=12, required=False)
    anio = serializers.IntegerField(min_value=1, max_value=9999, required=False)
    lugar = serializers.CharField(required=False, allow_blank=False)


class ReporteMensualParamsSerializer(serializers.Serializer):
    anio = serializers.IntegerField(min_value=2, max_value=9999)
    mes = serializers.IntegerField(min_value=1, max_value=12)


class ReporteAnualParamsSerializer(serializers.Serializer):
    anio = serializers.IntegerField(min_value=2, max_value=9999)

    def validate_anio(self, anio):
        if anio > timezone.localdate().year:
            raise serializers.ValidationError('No se permiten años futuros.')
        return anio


class PresentacionViewSet(
    CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin,
    GenericViewSet
):
    queryset = Presentacion.objects.select_related('persona_cargo').prefetch_related(
        'elencos', 'bitacora__coreografias'
    )
    serializer_class = PresentacionSerializer
    permission_classes = [PermisosPorModelo]

    @action(detail=False, methods=['get'], url_path='reporte-mensual')
    def reporte_mensual(self, request):
        parametros = ReporteMensualParamsSerializer(data=request.query_params.dict())
        parametros.is_valid(raise_exception=True)
        anio = parametros.validated_data['anio']
        mes = parametros.validated_data['mes']
        resumenes = resumenes_por_mes(anio, mes, primer_mes=mes)
        return Response({
            'mes': mes,
            'actual': resumenes[anio, mes],
            'anterior': resumenes[anio - 1, mes],
        })

    @action(detail=False, methods=['get'], url_path='reporte-anual')
    def reporte_anual(self, request):
        parametros = ReporteAnualParamsSerializer(data=request.query_params.dict())
        parametros.is_valid(raise_exception=True)
        anio = parametros.validated_data['anio']
        hoy = timezone.localdate()
        ultimo_mes = hoy.month if anio == hoy.year else 12
        resumenes = resumenes_por_mes(anio, ultimo_mes)
        return Response({
            'anio': anio,
            'anio_anterior': anio - 1,
            'meses': [
                {
                    'mes': mes,
                    'actual': resumenes[anio, mes],
                    'anterior': resumenes[anio - 1, mes],
                }
                for mes in range(1, ultimo_mes + 1)
            ],
        })

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
