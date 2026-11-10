import logging
from pathlib import PurePosixPath

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from usuarios.permisos import PermisosPorModelo
from .models import PlantillaCumpleanos, PublicacionRedSocial, TarjetaCumpleanos
from .serializers import (
    FiltroPublicacionesSerializer,
    PlantillaCumpleanosSerializer,
    PublicacionRedSocialSerializer,
    RechazoTarjetaSerializer,
    TarjetaCumpleanosSerializer,
)
from .services import (
    FacebookAPIError,
    detectar_cumpleanos,
    publicar_fotografia_facebook,
)


logger = logging.getLogger(__name__)


class PublicacionFacebookError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = 'No fue posible publicar la fotografía en Facebook.'
    default_code = 'error_publicacion_facebook'


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


class PublicacionRedSocialViewSet(ReadOnlyModelViewSet):
    queryset = PublicacionRedSocial.objects.select_related('tarjeta')
    serializer_class = PublicacionRedSocialSerializer
    permission_classes = [PermisosPorModelo]

    def get_queryset(self):
        queryset = super().get_queryset()
        filtros = FiltroPublicacionesSerializer(data=self.request.query_params)
        filtros.is_valid(raise_exception=True)
        datos = filtros.validated_data
        if 'estado' in datos:
            queryset = queryset.filter(estado=datos['estado'])
        if 'mes_desde' in datos:
            queryset = queryset.filter(
                fecha_publicacion__month__gte=datos['mes_desde'],
                fecha_publicacion__month__lte=datos['mes_hasta'],
                fecha_publicacion__year=datos.get('anio', timezone.localdate().year)
            )
        elif 'anio' in datos:
            queryset = queryset.filter(fecha_publicacion__year=datos['anio'])
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return Response({'data': self.get_serializer(queryset, many=True).data})

    def retrieve(self, request, *args, **kwargs):
        return Response({'data': [self.get_serializer(self.get_object()).data]})


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
        publicacion_confirmada = False
        id_publicacion = None
        try:
            with transaction.atomic():
                tarjeta = self._tarjeta_pendiente(pk)
                if not tarjeta.imagen:
                    raise ValidationError('La tarjeta no tiene un afiche para publicar.')
                publicacion = PublicacionRedSocial.objects.select_for_update().filter(
                    tarjeta=tarjeta,
                    plataforma=PublicacionRedSocial.Plataforma.FACEBOOK
                ).first()
                if publicacion and publicacion.estado == PublicacionRedSocial.Estado.PUBLICADA:
                    raise ValidationError(
                        'La tarjeta ya tiene una publicación en Facebook.'
                    )

                try:
                    with tarjeta.imagen.open('rb') as archivo:
                        resultado = publicar_fotografia_facebook(
                            archivo,
                            PurePosixPath(tarjeta.imagen.name).name,
                            tarjeta.mensaje_generado
                        )
                except FacebookAPIError as error:
                    raise PublicacionFacebookError(str(error)) from error
                except OSError as error:
                    logger.exception('No fue posible abrir el afiche de la tarjeta %s.', pk)
                    raise ValidationError(
                        'No fue posible abrir el afiche de la tarjeta.'
                    ) from error

                if resultado.get('publicada') is not True or not resultado.get('id'):
                    raise PublicacionFacebookError(
                        'Facebook no confirmó la publicación de la fotografía.'
                    )
                publicacion_confirmada = True
                id_publicacion = resultado.get('post_id') or resultado['id']
                fecha = timezone.now()
                PublicacionRedSocial.objects.update_or_create(
                    tarjeta=tarjeta,
                    plataforma=PublicacionRedSocial.Plataforma.FACEBOOK,
                    defaults={
                        'estado': PublicacionRedSocial.Estado.PUBLICADA,
                        'texto_publicacion': tarjeta.mensaje_generado,
                        'fecha_publicacion': fecha,
                        'id_publicacion_externa': id_publicacion,
                        'mensaje_error': '',
                    }
                )
                tarjeta.estado = TarjetaCumpleanos.Estado.APROBADA
                tarjeta.fecha_aprobacion = fecha
                tarjeta.aprobado_por = request.user
                tarjeta.save()
        except Exception:
            if publicacion_confirmada:
                logger.exception(
                    'La tarjeta %s se publicó en Facebook (id: %s), pero no se pudo '
                    'guardar la aprobación. Verifique la publicación antes de reintentar.',
                    pk, id_publicacion
                )
            raise
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
