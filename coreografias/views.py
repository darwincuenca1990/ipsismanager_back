from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from usuarios.permisos import PermisosPorModelo

from .models import Coreografia
from .serializers import CoreografiaSerializer


class CoreografiaViewSet(ModelViewSet):
    queryset = Coreografia.objects.all()
    serializer_class = CoreografiaSerializer
    permission_classes = [PermisosPorModelo]

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as error:
            raise ValidationError(
                'No se puede eliminar la coreografía porque está asociada a una presentación.'
            ) from error
