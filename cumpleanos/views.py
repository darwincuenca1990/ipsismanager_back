from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from usuarios.permisos import PermisosPorModelo
from .models import PlantillaCumpleanos, TarjetaCumpleanos
from .serializers import PlantillaCumpleanosSerializer
from .services import detectar_cumpleanos


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
