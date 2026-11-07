
from django.db.models import OuterRef, Subquery
from rest_framework.viewsets import ModelViewSet

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
