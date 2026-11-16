from .models import Parametro


def obtener_parametro(nombre, default=None):
    """Devuelve el valor del parámetro ACTIVO con ese nombre, o `default`."""
    valor = Parametro.objects.filter(
        nombre=nombre,
        estado=Parametro.Estado.ACTIVO
    ).values_list('valor', flat=True).first()
    return valor if valor not in (None, '') else default
