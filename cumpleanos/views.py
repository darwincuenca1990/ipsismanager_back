from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from usuarios.permisos import PermisosPorModelo
from .models import PlantillaCumpleanos, TarjetaCumpleanos
from .serializers import (
    PlantillaCumpleanosSerializer,
    RechazoTarjetaSerializer,
    TarjetaCumpleanosSerializer,
)
from .services import detectar_cumpleanos


class PuedeAprobarTarjetas(BasePermission):

    def has_permission(self, request, view):
        return request.user.has_perm(
            'cumpleanos.aprobar_tarjetacumpleanos'
        )


class PlantillaCumpleanosViewSet(ModelViewSet):
    queryset = PlantillaCumpleanos.objects.all()
    serializer_class = PlantillaCumpleanosSerializer
    permission_classes = [PermisosPorModelo]

    def get_queryset(self):
        queryset = super().get_queryset()
        elenco = self.request.query_params.get('elenco')

        if elenco is not None:
            choices = PlantillaCumpleanos.Elenco.values
            if elenco not in choices:
                raise ValidationError({
                    'elenco': (
                        f'Elenco no válido. Valores permitidos: '
                        f'{", ".join(choices)}.'
                    )
                })
            queryset = queryset.filter(elenco=elenco)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({'data': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response({'data': [serializer.data]})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'data': [serializer.data]},
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'data': [serializer.data]})


class DetectarCumpleanosView(APIView):
    queryset = TarjetaCumpleanos.objects.all()
    permission_classes = [PermisosPorModelo]

    def post(self, request):
        return Response(detectar_cumpleanos())


class TarjetaCumpleanosViewSet(ReadOnlyModelViewSet):
    queryset = TarjetaCumpleanos.objects.select_related(
        'bailarin',
        'aprobado_por',
        'rechazado_por'
    )
    serializer_class = TarjetaCumpleanosSerializer
    permission_classes = [PermisosPorModelo]

    def get_permissions(self):
        if self.action in ('aprobar', 'rechazar'):
            return [PuedeAprobarTarjetas()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        filtros = {
            'anio': 'anio',
            'estado': 'estado',
            'estado_generacion': 'estado_generacion',
        }
        for parametro, campo in filtros.items():
            valor = params.get(parametro)
            if valor:
                queryset = queryset.filter(**{campo: valor})
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({'data': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response({'data': [serializer.data]})

    def _tarjeta_pendiente(self, pk):
        tarjeta = TarjetaCumpleanos.objects.select_for_update().get(pk=pk)
        if (
            tarjeta.estado_generacion
            != TarjetaCumpleanos.EstadoGeneracion.GENERADA
        ):
            raise ValidationError(
                'Solo se pueden revisar tarjetas con afiche generado.'
            )
        if tarjeta.estado != TarjetaCumpleanos.Estado.PENDIENTE:
            raise ValidationError(
                'La tarjeta ya fue revisada: '
                f'{tarjeta.get_estado_display()}.'
            )
        return tarjeta

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        self.get_object()
        with transaction.atomic():
            tarjeta = self._tarjeta_pendiente(pk)
            tarjeta.estado = TarjetaCumpleanos.Estado.APROBADA
            tarjeta.fecha_aprobacion = timezone.now()
            tarjeta.aprobado_por = request.user
            tarjeta.save()
        return Response({'data': [self.get_serializer(tarjeta).data]})

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        self.get_object()
        serializer = RechazoTarjetaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            tarjeta = self._tarjeta_pendiente(pk)
            tarjeta.estado = TarjetaCumpleanos.Estado.RECHAZADA
            tarjeta.fecha_rechazo = timezone.now()
            tarjeta.rechazado_por = request.user
            tarjeta.motivo_rechazo = serializer.validated_data['motivo']
            tarjeta.save()
        return Response({'data': [self.get_serializer(tarjeta).data]})
