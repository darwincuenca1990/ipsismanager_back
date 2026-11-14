from rest_framework.routers import DefaultRouter

from .views import (
    AdquisicionTrajeViewSet,
    ComposicionTrajeViewSet,
    PrendaTrajeViewSet,
    TipoTrajeViewSet,
)

router = DefaultRouter()
router.register('tipos', TipoTrajeViewSet, basename='tipo-traje')
router.register('prendas', PrendaTrajeViewSet, basename='prenda-traje')
router.register('composiciones', ComposicionTrajeViewSet, basename='composicion-traje')
router.register('adquisiciones', AdquisicionTrajeViewSet, basename='adquisicion-traje')

urlpatterns = router.urls
