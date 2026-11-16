from rest_framework.routers import DefaultRouter

from .views import PresentacionViewSet


router = DefaultRouter()
router.register(r'presentaciones', PresentacionViewSet, basename='presentacion')

urlpatterns = router.urls
