
import time

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken


class LoginSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):

        data = super().validate(attrs)

        access_token = AccessToken(data['access'])

        expires_in = max(
            0,
            int(access_token['exp'] - time.time())
        )

        usuario = self.user

        # Determinar el rol del usuario
        if usuario.is_superuser:
            rol = 'Propietario'
        elif usuario.groups.filter(name='Administrador').exists():
            rol = 'Administrador'
        elif usuario.groups.filter(name='Dirección').exists():
            rol = 'Dirección'
        else:
            rol = 'Sin rol asignado'

        return {
            'data': {
                'access': data['access'],
                'refresh': data['refresh'],
                'expires_in': expires_in,

                'user': {
                    'username': usuario.username,
                    'correo': usuario.email,
                    'nombre': usuario.first_name,
                    'apellido': usuario.last_name,
                    'rol': rol,
                    'fechaRegistro': usuario.date_joined.isoformat(),
                }
            }
        }
