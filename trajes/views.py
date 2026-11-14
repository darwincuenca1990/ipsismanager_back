from decimal import Decimal

from django.db.models import Sum
from django.db.models.deletion import ProtectedError
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from usuarios.permisos import PermisosPorModelo

from .models import AdquisicionTraje, ComposicionTraje, Estado, PrendaTraje, TipoTraje
from .serializers import (
    AdquisicionTrajeSerializer,
    ComposicionTrajeSerializer,
    PrendaTrajeSerializer,
    TipoTrajeSerializer,
)


def _exigir_permiso(request, permiso):
    if not request.user.has_perm(permiso):
        raise PermissionDenied()


class TipoTrajeViewSet(ModelViewSet):
    queryset = TipoTraje.objects.all()
    serializer_class = TipoTrajeSerializer
    permission_classes = [PermisosPorModelo]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action == 'inactivar':
            return [PuedeInactivarTraje()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def inactivar(self, request, pk=None):
        traje = self.get_object()
        traje.estado = Estado.INACTIVO
        traje.save(update_fields=['estado', 'fecha_actualizacion'])
        return Response(self.get_serializer(traje).data)

    @action(detail=True, methods=['get'])
    def prendas(self, request, pk=None):
        _exigir_permiso(request, 'trajes.view_composiciontraje')
        traje = self.get_object()
        prendas = traje.composicion.select_related('prenda')
        return Response(ComposicionTrajeSerializer(
            prendas, many=True, context=self.get_serializer_context()
        ).data)

    @action(detail=True, methods=['get'], url_path='costo-estimado')
    def costo_estimado(self, request, pk=None):
        _exigir_permiso(request, 'trajes.view_composiciontraje')
        traje = self.get_object()
        composicion = traje.composicion.filter(
            estado=Estado.ACTIVO, prenda__estado=Estado.ACTIVO
        )
        subtotal = Decimal('0.00')
        sin_precio = []
        for item in composicion:
            if item.precio_unitario is None:
                sin_precio.append(item.pk)
            else:
                subtotal += item.cantidad_requerida * item.precio_unitario
        return Response({
            'tipo_traje': traje.pk,
            'subtotal': str(subtotal),
            'completo': not sin_precio,
            'composiciones_sin_precio': sin_precio,
        })

    @action(detail=True, methods=['get'])
    def adquisiciones(self, request, pk=None):
        _exigir_permiso(request, 'trajes.view_adquisiciontraje')
        traje = self.get_object()
        return Response(AdquisicionTrajeSerializer(
            traje.adquisiciones.all(), many=True, context=self.get_serializer_context()
        ).data)

    @action(detail=True, methods=['get'], url_path='resumen-adquisiciones')
    def resumen_adquisiciones(self, request, pk=None):
        _exigir_permiso(request, 'trajes.view_adquisiciontraje')
        traje = self.get_object()
        totales = traje.adquisiciones.aggregate(
            cantidad=Sum('cantidad_adquirida'), inversion=Sum('costo_total')
        )
        return Response({
            'tipo_traje': traje.pk,
            'cantidad_total_adquirida': totales['cantidad'] or 0,
            'inversion_total': str(totales['inversion'] or Decimal('0.00')),
        })


class PuedeInactivarTraje(PermisosPorModelo):
    perms_map = {**PermisosPorModelo.perms_map, 'POST': ['%(app_label)s.change_%(model_name)s']}


class PrendaTrajeViewSet(ModelViewSet):
    queryset = PrendaTraje.objects.all()
    serializer_class = PrendaTrajeSerializer
    permission_classes = [PermisosPorModelo]

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as error:
            raise ValidationError(
                'No se puede eliminar la prenda porque está asociada a un traje.'
            ) from error


class ComposicionTrajeViewSet(ModelViewSet):
    queryset = ComposicionTraje.objects.select_related('tipo_traje', 'prenda')
    serializer_class = ComposicionTrajeSerializer
    permission_classes = [PermisosPorModelo]

    def get_queryset(self):
        queryset = super().get_queryset()
        tipo_traje = self.request.query_params.get('tipo_traje')
        if tipo_traje:
            try:
                tipo_traje = int(tipo_traje)
                if tipo_traje < 1:
                    raise ValueError
            except ValueError as error:
                raise ValidationError({'tipo_traje': 'Indique un ID válido.'}) from error
            queryset = queryset.filter(tipo_traje_id=tipo_traje)
        return queryset


class AdquisicionTrajeViewSet(ModelViewSet):
    queryset = AdquisicionTraje.objects.select_related('tipo_traje')
    serializer_class = AdquisicionTrajeSerializer
    permission_classes = [PermisosPorModelo]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = super().get_queryset()
        tipo_traje = self.request.query_params.get('tipo_traje')
        if tipo_traje:
            try:
                tipo_traje = int(tipo_traje)
                if tipo_traje < 1:
                    raise ValueError
            except ValueError as error:
                raise ValidationError({'tipo_traje': 'Indique un ID válido.'}) from error
            queryset = queryset.filter(tipo_traje_id=tipo_traje)
        return queryset
