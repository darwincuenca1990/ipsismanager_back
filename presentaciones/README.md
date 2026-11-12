# Presentaciones

Los servicios requieren autenticación y permisos de modelo: `view_presentacion`,
`add_presentacion` y `change_presentacion`.

- `POST /api/presentaciones/`: crear.
- `GET /api/presentaciones/`: listar, opcionalmente filtrando con `mes` (1-12),
  `anio` (1-9999) y `lugar` (búsqueda parcial sin distinguir mayúsculas).
  Los filtros se combinan.
- `GET /api/presentaciones/{id}/`: consultar una presentación.
- `PUT` o `PATCH /api/presentaciones/{id}/`: actualizar.
- `GET /api/presentaciones/reporte-mensual/?anio=2026&mes=11`: resumen
  del mes solicitado y del mismo mes del año anterior.
- `GET /api/presentaciones/reporte-anual/?anio=2026`: resumen por mes del año
  solicitado y del año anterior. Para el año actual llega hasta el mes actual;
  para años anteriores incluye los 12 meses. No admite años futuros.

Ambos reportes requieren el permiso `view_presentacion`. Los parámetros son
obligatorios; `anio` debe estar entre 2 y 9999 y `mes` entre 1 y 12. Se incluyen
los meses completos, incluso las presentaciones programadas. Cada resumen
contiene `anio`, `cantidad_presentaciones`, `ids_presentaciones`,
`costo_total_presentacion`, `costo_transporte` y `costo_neto`. Los importes son
cadenas decimales con dos posiciones y el neto es el bruto menos el transporte.
Los meses sin presentaciones tienen conteo cero, lista vacía e importes `"0.00"`.

El reporte mensual devuelve `{ "mes": 11, "actual": {...}, "anterior": {...} }`.
El anual devuelve `{ "anio": 2026, "anio_anterior": 2025, "meses": [...] }`;
cada elemento de `meses` tiene la misma estructura que el reporte mensual.

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
