from calendar import isleap, monthrange
from datetime import date
from datetime import timedelta
from functools import reduce
from operator import or_

from django.http import Http404, HttpResponse
from django.db.models import Case, IntegerField, OuterRef, Q, Subquery, Value, When
from django.db.models.deletion import ProtectedError
from django.db.models.functions import ExtractDay
from django.utils import timezone
from django.utils.http import content_disposition_header
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .google_drive import GoogleDriveFileNotFound, download_bailarin_photo
from .models import Bailarin, GrupoFamiliar, Inscripcion
from .serializers import (
    BailarinSerializer,
    CumpleanosMesParamsSerializer,
    CumpleanosSemanaParamsSerializer,
    GrupoFamiliarSerializer,
    InscripcionSerializer,
)

from usuarios.permisos import PermisosPorModelo


class BailarinViewSet(ModelViewSet):

    queryset = Bailarin.objects.select_related(
        'grupo_familiar'
    ).all()

    serializer_class = BailarinSerializer

    permission_classes = [PermisosPorModelo]

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as error:
            raise ValidationError(
                'No se puede eliminar el bailarín porque tiene registros asociados.'
            ) from error

    @action(detail=False, methods=['get'], url_path='candidatos-elenco-planta')
    def candidatos_elenco_planta(self, request):
        hoy = timezone.localdate()
        anio_limite = hoy.year + (hoy.month + 5) // 12
        mes_limite = (hoy.month + 5) % 12 + 1
        dia_limite = min(hoy.day, monthrange(anio_limite, mes_limite)[1])
        fecha_limite = date(anio_limite, mes_limite, dia_limite)

        anio_nacimiento = fecha_limite.year - 14
        dia_nacimiento = min(
            fecha_limite.day, monthrange(anio_nacimiento, fecha_limite.month)[1]
        )
        nacimiento_limite = date(
            anio_nacimiento, fecha_limite.month, dia_nacimiento
        )
        edad_valida = Q(fecha_nacimiento__lte=nacimiento_limite)
        if (
            fecha_limite.month == 2
            and fecha_limite.day == 28
            and not isleap(fecha_limite.year)
            and isleap(anio_nacimiento)
        ):
            edad_valida |= Q(fecha_nacimiento=date(anio_nacimiento, 2, 29))

        bailarines = self.get_queryset().filter(
            edad_valida, elenco=Bailarin.Elenco.INFANTIL
        ).order_by('fecha_nacimiento', 'apellidos', 'nombres', 'pk')
        return Response({
            'fecha_actual': hoy.isoformat(),
            'fecha_limite': fecha_limite.isoformat(),
            'data': self.get_serializer(bailarines, many=True).data,
        })

    @action(detail=False, methods=['get'], url_path='cumpleanos-semana')
    def cumpleanos_semana(self, request):
        parametros = CumpleanosSemanaParamsSerializer(data=request.query_params)
        parametros.is_valid(raise_exception=True)
        desplazamiento = {'anterior': -1, 'actual': 0, 'siguiente': 1}[
            parametros.validated_data['semana']
        ]
        hoy = timezone.localdate()
        inicio = hoy - timedelta(days=(hoy.weekday() + 1) % 7)
        inicio += timedelta(weeks=desplazamiento)
        fechas = [inicio + timedelta(days=dia) for dia in range(7)]
        condiciones = [
            Q(fecha_nacimiento__month=fecha.month, fecha_nacimiento__day=fecha.day)
            for fecha in fechas
        ]
        bailarines = self.get_queryset().filter(
            reduce(or_, condiciones)
        ).annotate(
            orden_cumpleanos=Case(
                *[
                    When(condicion, then=Value(indice))
                    for indice, condicion in enumerate(condiciones)
                ],
                output_field=IntegerField()
            )
        ).order_by('orden_cumpleanos', 'apellidos', 'nombres', 'pk')
        return Response({
            'fecha_inicio': inicio.isoformat(),
            'fecha_fin': fechas[-1].isoformat(),
            'data': self.get_serializer(bailarines, many=True).data,
        })

    @action(detail=False, methods=['get'], url_path='cumpleanos-mes')
    def cumpleanos_mes(self, request):
        parametros = CumpleanosMesParamsSerializer(data=request.query_params)
        parametros.is_valid(raise_exception=True)
        mes = parametros.validated_data['mes']
        bailarines = self.get_queryset().filter(
            fecha_nacimiento__month=mes
        ).annotate(
            dia_cumpleanos=ExtractDay('fecha_nacimiento')
        ).order_by('dia_cumpleanos', 'apellidos', 'nombres', 'pk')
        return Response({
            'mes': mes,
            'data': self.get_serializer(bailarines, many=True).data,
        })

    @action(
        detail=True,
        methods=['get'],
        url_path='fotografia'
    )
    def fotografia(self, request, pk=None):
        bailarin = self.get_object()
        if not bailarin.fotografia_drive_id:
            raise Http404('Este bailarín no tiene fotografía.')

        try:
            photo = download_bailarin_photo(
                bailarin.fotografia_drive_id
            )
        except GoogleDriveFileNotFound as error:
            raise Http404('No se encontró la fotografía.') from error

        response = HttpResponse(
            photo['content'],
            content_type=photo['mime_type']
        )
        response['Content-Disposition'] = content_disposition_header(
            False,
            photo['name']
        )
        return response

    def get_queryset(self):
        queryset = super().get_queryset()
        elenco = self.request.query_params.get('elenco')
        estado = self.request.query_params.get('estado')

        ultima_inscripcion = Inscripcion.objects.filter(
            bailarin=OuterRef('pk')
        ).order_by(
            '-fecha_ingreso_agrupacion',
            '-id'
        )
        queryset = queryset.annotate(
            inscripcion_fecha_ingreso_agrupacion=Subquery(
                ultima_inscripcion.values(
                    'fecha_ingreso_agrupacion'
                )[:1]
            ),
            inscripcion_estado=Subquery(
                ultima_inscripcion.values('estado')[:1]
            ),
            inscripcion_motivo_ingreso_agrupacion=Subquery(
                ultima_inscripcion.values(
                    'motivo_ingreso_agrupacion'
                )[:1]
            ),
            inscripcion_fecha_salida=Subquery(
                ultima_inscripcion.values('fecha_salida')[:1]
            ),
        )

        if elenco and elenco.lower() != 'todos':
            queryset = queryset.filter(elenco=elenco)

        if estado:
            queryset = queryset.filter(inscripcion_estado=estado)

        return queryset


class GrupoFamiliarViewSet(ModelViewSet):

    queryset = GrupoFamiliar.objects.all()

    serializer_class = GrupoFamiliarSerializer

    permission_classes = [PermisosPorModelo]


class InscripcionViewSet(ModelViewSet):

    queryset = Inscripcion.objects.select_related(
        'bailarin'
    ).all()

    serializer_class = InscripcionSerializer

    permission_classes = [PermisosPorModelo]
