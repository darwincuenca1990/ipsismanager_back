# Inventario de trajes

Todos los endpoints requieren autenticación y permisos de modelo Django
(`view`, `add`, `change`, `delete`). Una lectura de datos relacionados desde
un traje también requiere el permiso `view` del modelo relacionado.
Después de migrar, asignar los permisos nuevos a los grupos correspondientes.
El comando existente `python manage.py configurar_roles` actualiza los permisos
del Administrador, pero también reemplaza los permisos del grupo Dirección por
su configuración predeterminada; revisar este efecto antes de ejecutarlo.

- `GET/POST /api/trajes/tipos/`, `GET/PUT/PATCH /api/trajes/tipos/{id}/`:
  administrar tipos. `POST /api/trajes/tipos/{id}/inactivar/` requiere
  `change_tipotraje`. No se elimina el catálogo.
- `GET/POST /api/trajes/prendas/`, `GET/PUT/PATCH/DELETE /api/trajes/prendas/{id}/`:
  catálogo reutilizable. Una prenda asociada a un traje no puede eliminarse.
- `GET/POST /api/trajes/composiciones/`,
  `GET/PUT/PATCH/DELETE /api/trajes/composiciones/{id}/`: asociar una prenda
  existente a un tipo; requiere `tipo_traje`, `prenda` y `cantidad_requerida`.
  La cantidad y el `precio_unitario` opcional son propios de esa asociación.
  Filtrar por `?tipo_traje={id}` o consultar
  `GET /api/trajes/tipos/{id}/prendas/`. No se admiten asociaciones duplicadas.
- `GET /api/trajes/tipos/{id}/costo-estimado/`: suma cantidad por precio de
  asociaciones y prendas activas. Devuelve `subtotal`, `completo` y los IDs
  `composiciones_sin_precio`. Si no hay precios faltantes, `completo` es true.
- `GET/POST /api/trajes/adquisiciones/`,
  `GET/PUT/PATCH /api/trajes/adquisiciones/{id}/`: registrar y actualizar
  compras; permite filtrar con `?tipo_traje={id}`. El `costo_total` se calcula
  como cantidad por costo unitario; no se acepta del cliente. El historial no
  puede eliminarse mediante la API.
- `GET /api/trajes/tipos/{id}/adquisiciones/` devuelve el historial y
  `GET /api/trajes/tipos/{id}/resumen-adquisiciones/` devuelve cantidad e
  inversión totales; un traje sin compras devuelve cero.

Cantidades deben ser positivas y precios no negativos. Las fotografías y
comprobantes se envían mediante `multipart/form-data`; se almacenan usando el
almacenamiento de archivos configurado en Django. La composición es actual,
no una instantánea histórica de cada compra; se permite modificarla después de
una adquisición.
