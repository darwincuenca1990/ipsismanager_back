from rest_framework.routers import DefaultRouter

from .views import CoreografiaViewSet


router = DefaultRouter()
router.register(r'coreografias', CoreografiaViewSet, basename='coreografia')

urlpatterns = router.urls
