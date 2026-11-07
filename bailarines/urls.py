
from rest_framework.routers import DefaultRouter

from .views import (
    BailarinViewSet,
    GrupoFamiliarViewSet,
    InscripcionViewSet,
)

router = DefaultRouter()

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

urlpatterns = router.urls
