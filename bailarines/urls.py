
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BailarinViewSet,
    GrupoFamiliarViewSet,
    InscripcionViewSet,
)

router = DefaultRouter()

fotografia_bailarin_view = BailarinViewSet.as_view({'get': 'fotografia'})

urlpatterns = [
    path(
        'bailarines//<int:pk>/fotografia/',
        fotografia_bailarin_view,
        name='bailarin-fotografia-double-slash',
    ),
]

router.register(
    r'bailarines',
    BailarinViewSet,
    basename='bailarin'
)

router.register(
    r'grupos-familiares',
    GrupoFamiliarViewSet,
    basename='grupo-familiar'
)

router.register(
    r'inscripciones',
    InscripcionViewSet,
    basename='inscripcion'
)

urlpatterns += router.urls
