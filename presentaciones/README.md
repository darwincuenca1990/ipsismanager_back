# Presentaciones

Los servicios requieren autenticación y permisos de modelo: `view_presentacion`,
`add_presentacion` y `change_presentacion`.

- `POST /api/presentaciones/`: crear.
- `GET /api/presentaciones/`: listar, opcionalmente filtrando con `mes` (1-12),
  `anio` (1-9999) y `lugar` (búsqueda parcial sin distinguir mayúsculas).
  Los filtros se combinan.
- `GET /api/presentaciones/{id}/`: consultar una presentación.
- `PUT` o `PATCH /api/presentaciones/{id}/`: actualizar.

Ejemplo de creación:

```json
{
  "fecha": "2026-11-25",
  "lugar": "Teatro",
  "hora_presentacion": "19:30:00",
  "persona_cargo": 1,
  "costo_total_presentacion": "500.00",
  "costo_transporte": "100.00",
  "nombre_transporte": "Bus",
  "tipo_presentacion": "FESTIVALIPSIS",
  "elencos": ["INFANTIL", "PLANTA"],
  "bitacora": [
    {"bailarin": 1, "coreografias": [1, 2]},
    {"bailarin": 2, "coreografias": [2]}
  ]
}
```

`persona_cargo`, `bailarin` y `coreografias` son identificadores existentes.
Para `UN ELENCO` se requiere exactamente un elemento en `elencos`; para
`FESTIVALIPSIS` se permite uno o varios. La bitácora puede omitirse o estar vacía,
y cada bailarín puede tener una lista vacía de coreografías.

`costo_neto` es de solo lectura y se calcula como el costo total menos el costo
de transporte. En una actualización, si se envían `elencos` o `bitacora`, la lista
enviada reemplaza completamente la anterior; si se omiten, se conservan. Cada
entrada enviada en `bitacora` debe incluir `bailarin` y `coreografias`.
