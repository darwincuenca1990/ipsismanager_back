from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import (
    DetectarCumpleanosView,
    PlantillaCumpleanosViewSet,
    TarjetaCumpleanosViewSet,
)


router = DefaultRouter()
router.register(
    r'tarjetas',
    TarjetaCumpleanosViewSet,
    basename='tarjeta-cumpleanos'
)
router.register(
    r'plantillas',
    PlantillaCumpleanosViewSet,
    basename='plantilla-cumpleanos'
)

urlpatterns = [
    path(
        'detector/',
        DetectarCumpleanosView.as_view(),
        name='detectar-cumpleanos'
    ),
] + router.urls
