
from django.http import Http404, HttpResponse
from django.db.models import OuterRef, Subquery
from django.utils.http import content_disposition_header
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from .google_drive import GoogleDriveFileNotFound, download_bailarin_photo
from .models import Bailarin, GrupoFamiliar, Inscripcion
from .serializers import (
    BailarinSerializer,
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

        if elenco and elenco.lower() != 'todos':
            queryset = queryset.filter(elenco=elenco)

        if estado:
            ultima_inscripcion = Inscripcion.objects.filter(
                bailarin=OuterRef('pk')
            ).order_by(
                '-fecha_ingreso_agrupacion',
                '-id'
            )
            queryset = queryset.annotate(
                estado_inscripcion=Subquery(
                    ultima_inscripcion.values('estado')[:1]
                )
            ).filter(estado_inscripcion=estado)

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
