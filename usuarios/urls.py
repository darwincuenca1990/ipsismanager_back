
from django.urls import path

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from .serializers import LoginSerializer
from .views import UsuarioActualView, LogoutView

from rest_framework_simplejwt.views import TokenObtainPairView


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

from .google_oauth import (
    google_drive_authorize,
    google_drive_callback,
)
urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', UsuarioActualView.as_view(), name='usuario_actual'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path(
        'google/authorize/',
        google_drive_authorize,
        name='google_drive_authorize'
    ),
    path(
        'google/callback/',
        google_drive_callback,
        name='google_drive_callback'
    ),
]

