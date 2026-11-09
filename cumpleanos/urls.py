from rest_framework.routers import DefaultRouter

from .views import PlantillaCumpleanosViewSet


router = DefaultRouter()
router.register(
    r'plantillas',
    PlantillaCumpleanosViewSet,
    basename='plantilla-cumpleanos'
)

urlpatterns = router.urls
