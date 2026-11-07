# Inventario del esquema legado — Pinturas JAM

Fuente: `app.py` en la rama de migración, función `inicializar_db()` y operaciones de rutas.
Estado: inspección estática del código. La base Supabase destino está restaurándose y todavía no permite introspección. Este documento NO sustituye el respaldo de producción.

## Tablas exactas identificadas en el código

### `productos`
- `id SERIAL PRIMARY KEY`
- `nombre TEXT NOT NULL`
- `color TEXT NOT NULL`
- `precio NUMERIC NOT NULL`
- `stock_actual INTEGER NOT NULL`
- `stock_minimo INTEGER NOT NULL`
- `categoria TEXT DEFAULT 'Pinturas y Acabados'`

### `cierres_diarios`
- `id SERIAL PRIMARY KEY`
- `fecha DATE DEFAULT CURRENT_DATE`
- `tasa_bcv REAL`
- `total_pago_movil_bs REAL`
- `total_punto_bs REAL`
- `total_efectivo_usd REAL`
- `total_usdt REAL`
- `notas TEXT`

### `historial_ventas`
- `id SERIAL PRIMARY KEY`
- `producto_nombre TEXT NOT NULL`
- `precio NUMERIC NOT NULL`
- `comprador TEXT DEFAULT 'Consumidor Final'`
- `metodo_pago TEXT DEFAULT 'Efectivo'`
- `cantidad INTEGER DEFAULT 1`
- `total NUMERIC DEFAULT 0.0`
- `fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### `historial_compras`
- `id SERIAL PRIMARY KEY`
- `producto_id INTEGER NOT NULL` (el código no declara FK)
- `producto_nombre TEXT NOT NULL`
- `proveedor TEXT NOT NULL`
- `costo_unitario NUMERIC NOT NULL`
- `cantidad INTEGER NOT NULL`
- `costo_total NUMERIC NOT NULL`
- `fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### `usuarios`
- `id SERIAL PRIMARY KEY`
- `username TEXT UNIQUE NOT NULL`
- `password TEXT NOT NULL`

### `clientes_credito`
- `id SERIAL PRIMARY KEY`
- `nombre TEXT UNIQUE NOT NULL`
- `saldo NUMERIC DEFAULT 0.0`
- `ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### `movimientos_credito`
- `id SERIAL PRIMARY KEY`
- `cliente_id INTEGER REFERENCES clientes_credito(id)`
- `tipo TEXT NOT NULL`
- `monto NUMERIC NOT NULL`
- `descripcion TEXT`
- `fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### `configuracion`
- `id SERIAL PRIMARY KEY`
- `tasa_bcv NUMERIC DEFAULT 36.50`
- `ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

## Reglas de negocio observadas

- El inventario disminuye en venta simple y venta múltiple; aumenta al registrar compras.
- La compra editada modifica stock por diferencia; borrar compra resta su cantidad al stock actual.
- La venta a crédito genera un cargo en el libro de movimientos del cliente.
- Un abono reduce saldo, crea un movimiento `Abono` y también crea una fila en `historial_ventas` con `producto_nombre = 'ABONO A CUENTA'`.
- La tasa BCV se guarda en `configuracion`; cierres guardan una tasa por fecha.
- Las cotizaciones se renderizan para impresión pero no se encontró tabla persistente para cotizaciones.
- No se encontró tabla separada para facturas, pagos mixtos, anulaciones, auditoría ni Kardex histórico.

## Restricciones de migración

- No asumir que una fila de `historial_ventas` equivale a factura fiscal ni agrupar filas por comprador/fecha sin identificador documental.
- No inferir movimientos de Kardex previos a partir del saldo actual. Registrar saldo de apertura con referencia a la fecha de corte.
- Importar fechas, valores NUMERIC e IDs originales sin pérdida de precisión.
- No importar hashes inexistentes ni contraseñas en claro a Supabase Auth. Crear identidades nuevas con invitación/restablecimiento de contraseña.
- Conciliar saldos de crédito contra cargos/abonos; preservar saldo de origen y reportar diferencias, sin corregirlas automáticamente.
- Mantener la fuente de respaldo inmutable y conservar tabla/ID de origen para trazabilidad.

## Siguiente paso obligatorio

Esperar respaldo completo PostgreSQL de Render (`.dump` preferido o `.sql`). La restauración de destino Supabase debe terminar y permitir inspección de tablas antes de aplicar cualquier DDL. El proyecto destino identificado es `llxvprjmoiuslprqoewv`; no se ha aplicado ninguna migración ni se han importado filas.
