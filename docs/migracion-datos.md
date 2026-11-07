# Plan de migración — Pinturas JAM

## Estado y alcance

- Rama de trabajo: `migration/supabase-vercel-v2`
- Base de partida: commit `a4e29be8456363f7ec7f2b7c7da39f23bee11ee5`
- Producción: permanece en `main`; esta rama no se despliega ni se mezcla automáticamente.
- Estrategia de datos: conservar el origen íntegro, migrar a un entorno Supabase separado y validar antes de cualquier corte.
- No guardar respaldos, dumps, credenciales ni datos personales/comerciales en Git.

## Aplicación de origen identificada

El backend revisado es Flask + psycopg2 + PostgreSQL + Jinja2. El esquema se crea desde `inicializar_db()` en `app.py`. No es una aplicación frontend independiente; hay que migrar reglas de negocio y operaciones transaccionales además de las pantallas.

### Tablas y correspondencia inicial

| Origen PostgreSQL | Campos / contenido | Destino conceptual |
|---|---|---|
| `productos` | id, nombre, color, precio, stock_actual, stock_minimo, categoria | `products` + `inventory_balances` + movimiento inicial de apertura |
| `historial_ventas` | id, producto_nombre, precio, comprador, metodo_pago, cantidad, total, fecha | `sales` + `sale_items` + `payments` / `receivables`, conservando cada fila original |
| `historial_compras` | id, producto_id, producto_nombre, proveedor, costo_unitario, cantidad, costo_total, fecha | `purchases` + `purchase_items` + `suppliers` |
| `clientes_credito` | id, nombre, saldo, ultima_actualizacion | `customers` + saldo inicial conciliado |
| `movimientos_credito` | id, cliente_id, tipo, monto, descripcion, fecha | `customer_ledger` |
| `cierres_diarios` | id, fecha, tasa_bcv, totales por método, notas | `cash_closings` |
| `configuracion` | tasa_bcv, ultima_actualizacion | `exchange_rates` / configuración inicial |
| `usuarios` | id, username, password | Supabase Auth + `profiles` / `user_roles`; nunca copiar contraseñas en texto plano |

Los nombres definitivos de tablas destino se fijarán en la migración SQL después de revisar el respaldo real, incluyendo columnas, tipos, restricciones, secuencias, índices y datos existentes.

## Riesgos de integridad detectados en el modelo legado

1. Las ventas están guardadas como filas por producto, sin identificador de factura/venta padre. No se debe inventar agrupación de varias filas en una factura si no existe evidencia fiable.
2. Los abonos de crédito también se insertan en `historial_ventas` con producto `ABONO A CUENTA`. El importador debe clasificarlos como cobros/abonos cuando puedan vincularse a `movimientos_credito`; no deben contarse como ventas de mercancía.
3. El stock actual es un valor mutable en `productos`; no existe un Kardex completo. Se conservará exactamente el saldo de apertura y se crearán movimientos de apertura identificados como migración, sin fingir que se conocen movimientos históricos no registrados.
4. Las compras pueden editarse o eliminarse y alterar stock. El histórico disponible representa el estado que quedó almacenado, no necesariamente cada operación original.
5. Las cotizaciones no aparecen persistidas en las tablas revisadas. No se pueden reconstruir cotizaciones antiguas desde este esquema.
6. El saldo de clientes debe conciliarse contra los movimientos de crédito. Si hay diferencias, se conserva el saldo original y se registra una incidencia; no se ajusta silenciosamente.
7. Los cierres diarios y los totales de caja deben conservar su granularidad y valores originales, aunque no coincidan con sumas recalculadas.

## Procedimiento de migración

1. Obtener un respaldo PostgreSQL completo desde el proveedor de producción (preferiblemente `.dump` custom y además `.sql` cuando sea posible). No enviar contraseñas ni URLs con secretos por el chat.
2. Restaurar el respaldo en una base temporal aislada; no conectar el importador con la base productiva para escritura.
3. Inspeccionar `pg_dump --schema-only`, restricciones, secuencias, triggers, recuentos y rangos de fechas.
4. Construir una capa de staging que guarde cada fila original con su tabla e ID legado.
5. Transformar y cargar en transacciones repetibles e idempotentes, usando claves de origen únicas (`legacy_source`, `legacy_table`, `legacy_id`).
6. Conservar IDs de origen y fechas; no convertir importes mediante float. Usar `NUMERIC` y normalizar a la moneda/unidad únicamente cuando el origen lo permita.
7. Validar recuentos, sumas, saldos, stock, fechas mínimas/máximas y relaciones huérfanas por tabla.
8. Ejecutar pruebas funcionales con una copia anonimizada; revisar diferencias antes de habilitar usuarios.
9. Hacer ensayo de corte con respaldo nuevo, congelación breve de escrituras y conciliación final. Producción seguirá en el sistema anterior hasta aprobación explícita.

## Criterios de aceptación

- 100% de las filas de origen incluidas en staging o justificadas en un informe de excepciones.
- IDs de origen preservados y ninguna fila duplicada al reintentar la importación.
- Stock por producto idéntico al saldo de origen al cierre del corte.
- Saldos de crédito y movimientos conciliados; diferencias documentadas.
- Totales históricos por fecha y método de pago comparados, distinguiendo abonos de ventas.
- Totales de compras y cierres diarios comparados con el origen.
- Ningún secreto ni contraseña en texto plano transferido al frontend o al repositorio.
- RLS probada para cada rol y tablas expuestas; acceso administrativo asignado desde un canal seguro.

## Requisitos pendientes para ejecutar la migración real

- Respaldo de PostgreSQL de Render/producción (archivo `.dump` o `.sql`).
- Acceso/configuración del proyecto Supabase de destino mediante conexión segura en el entorno de ejecución; no pegar claves `service_role`, secret keys ni contraseñas en GitHub o en el chat.
- Confirmar la zona horaria operativa de la tienda para interpretar fechas de caja y ventas.

## Seguridad inmediata

El código legado contiene una clave de sesión y credenciales iniciales embebidas, y autentica comparando contraseñas en texto plano. Deben rotarse las credenciales y la clave de sesión en el sistema actual por un canal seguro. En la nueva versión se usará Supabase Auth; las autorizaciones se guardarán en roles controlados por servidor/base de datos, nunca en `user_metadata` editable por el usuario.
