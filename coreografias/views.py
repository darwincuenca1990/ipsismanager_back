from rest_framework.viewsets import ModelViewSet

from usuarios.permisos import PermisosPorModelo

from .models import Coreografia
from .serializers import CoreografiaSerializer


class CoreografiaViewSet(ModelViewSet):
    queryset = Coreografia.objects.all()
    serializer_class = CoreografiaSerializer
    permission_classes = [PermisosPorModelo]
