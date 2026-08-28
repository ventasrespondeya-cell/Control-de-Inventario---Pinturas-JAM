from flask import Flask, render_template, request, redirect, url_for, Response, session
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
import psycopg2
from psycopg2.extras import RealDictCursor
import csv
import io
import os

app = Flask(__name__)
app.secret_key = 'J4m_P1ntur4s#2026!k9$mX8zQ2Lp_SecureKey'

# Configuración de ProxyFix para Render
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

def conectar_db():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        raise Exception("Falta configurar la variable DATABASE_URL en Render")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def inicializar_db():
    if not os.environ.get('DATABASE_URL'):
        return
        
    conn = conectar_db()
    cursor = conn.cursor()
    
    # --- TUS TABLAS INTACTAS ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS productos (
                        id SERIAL PRIMARY KEY, 
                        nombre TEXT NOT NULL, 
                        color TEXT NOT NULL, 
                        precio NUMERIC NOT NULL, 
                        stock_actual INTEGER NOT NULL, 
                        stock_minimo INTEGER NOT NULL,
                        categoria TEXT DEFAULT 'Pinturas y Acabados')''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS historial_ventas (
                        id SERIAL PRIMARY KEY, 
                        producto_nombre TEXT NOT NULL, 
                        precio NUMERIC NOT NULL,
                        comprador TEXT DEFAULT 'Consumidor Final',
                        metodo_pago TEXT DEFAULT 'Efectivo',
                        cantidad INTEGER DEFAULT 1,
                        total NUMERIC DEFAULT 0.0,
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS historial_compras (
                        id SERIAL PRIMARY KEY, 
                        producto_id INTEGER NOT NULL,
                        producto_nombre TEXT NOT NULL,
                        proveedor TEXT NOT NULL, 
                        costo_unitario NUMERIC NOT NULL, 
                        cantidad INTEGER NOT NULL, 
                        costo_total NUMERIC NOT NULL, 
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL)''')
    
    # --- NUEVA TABLA PARA GUARDAR LA TASA BCV ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS configuracion (
                        id SERIAL PRIMARY KEY,
                        tasa_bcv NUMERIC DEFAULT 0.0,
                        ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # --- TUS USUARIOS INTACTOS ---
    cursor.execute("SELECT COUNT(*) as conteo FROM usuarios")
    resultado = cursor.fetchone()
    if resultado['conteo'] == 0:
        cursor.execute("INSERT INTO usuarios (username, password) VALUES (%s, %s)", ("gerente", "G3r3nt3#JAM.2026!x9"))
        cursor.execute("INSERT INTO usuarios (username, password) VALUES (%s, %s)", ("suegra", "Adm1n_JAM#9876!z"))
    
    # --- CREAR LA TASA INICIAL SI NO EXISTE ---
    cursor.execute("SELECT COUNT(*) as conteo FROM configuracion")
    res_conf = cursor.fetchone()
    if res_conf['conteo'] == 0:
        cursor.execute("INSERT INTO configuracion (tasa_bcv) VALUES (36.50)")
        
    conn.commit()
    conn.close()

inicializar_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = %s AND password = %s", (usuario, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['usuario'] = usuario
            return redirect(url_for('inicio'))
        else:
            error = "Credenciales incorrectas. Intente de nuevo."
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
def usuarios():
    if session.get('usuario') != 'gerente':
        return redirect(url_for('inicio'))
        
    conn = conectar_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        nuevo_user = request.form['username']
        nueva_pass = request.form['password']
        
        cursor.execute("SELECT * FROM usuarios WHERE username = %s", (nuevo_user,))
        existe = cursor.fetchone()
        
        if existe:
            cursor.execute("UPDATE usuarios SET password = %s WHERE username = %s", (nueva_pass, nuevo_user))
        else:
            cursor.execute("INSERT INTO usuarios (username, password) VALUES (%s, %s)", (nuevo_user, nueva_pass))
            
        conn.commit()
        conn.close()
        return redirect(url_for('usuarios'))
        
    cursor.execute("SELECT * FROM usuarios")
    lista_usuarios = cursor.fetchall()
    conn.close()
    return render_template('usuarios.html', lista_usuarios=lista_usuarios)

@app.route('/')
@login_required
def inicio():
    busqueda = request.args.get('busqueda', '')
    conn = conectar_db()
    cursor = conn.cursor()
    
    # OBTENER TASA BCV DE LA BASE DE DATOS
    cursor.execute("SELECT tasa_bcv, TO_CHAR(ultima_actualizacion, 'DD/MM/YYYY HH12:MI AM') as fecha_act FROM configuracion LIMIT 1")
    res_tasa = cursor.fetchone()
    
    if res_tasa:
        tasa_bcv = float(res_tasa['tasa_bcv']) if res_tasa['tasa_bcv'] else 36.50
        fecha_act = res_tasa['fecha_act'] if res_tasa['fecha_act'] else "Sin registro"
    else:
        tasa_bcv = 36.50
        fecha_act = "Sin registro"

    if busqueda:
        cursor.execute("SELECT * FROM productos WHERE nombre ILIKE %s OR color ILIKE %s OR categoria ILIKE %s ORDER BY id ASC", (f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%'))
    else:
        cursor.execute("SELECT * FROM productos ORDER BY id ASC")
    
    productos = cursor.fetchall()
    
    categorias = ['Flexiplack', 'Cuñete', 'Galón', 'Herramientas', 'Otros']
    productos_agrupados = {cat: [] for cat in categorias}
    
    for p in productos:
        cat_prod = (p['categoria'] or '').strip()
        cat_asignada = 'Otros'
        for cat_def in ['Flexiplack', 'Cuñete', 'Galón', 'Herramientas']:
            if cat_def.lower() in cat_prod.lower():
                cat_asignada = cat_def
                break
        productos_agrupados[cat_asignada].append(p)
    
    cursor.execute("SELECT SUM(precio * stock_actual) as total FROM productos")
    resultado_total = cursor.fetchone()
    valor_total = float(resultado_total['total']) if resultado_total and resultado_total['total'] else 0.0
    
    conn.close()
    
    return render_template('index.html', productos=productos, categorias=categorias, productos_agrupados=productos_agrupados, busqueda=busqueda, valor_total=valor_total, tasa_bcv=tasa_bcv, fecha_act=fecha_act)

# --- NUEVA RUTA PARA QUE EL GERENTE CAMBIE LA TASA ---
@app.route('/actualizar_tasa', methods=['POST'])
@login_required
def actualizar_tasa():
    if session.get('usuario') != 'gerente':
        return redirect(url_for('inicio')) # Solo el gerente puede cambiarla
        
    nueva_tasa = request.form.get('tasa_bcv')
    if nueva_tasa:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE configuracion SET tasa_bcv = %s, ultima_actualizacion = CURRENT_TIMESTAMP", (nueva_tasa,))
        conn.commit()
        conn.close()
    return redirect(url_for('inicio'))

@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    categorias = ['Flexiplack', 'Cuñete', 'Galón', 'Herramientas', 'Otros']
    if request.method == 'POST':
        categoria = request.form['categoria']
        nombre = request.form['nombre']
        color = request.form['color']
        precio = request.form['precio']
        stock_actual = request.form['stock_actual']
        stock_minimo = request.form['stock_minimo']
        
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO productos (categoria, nombre, color, precio, stock_actual, stock_minimo) 
                          VALUES (%s, %s, %s, %s, %s, %s)''', 
                       (categoria, nombre, color, precio, stock_actual, stock_minimo))
        conn.commit()
        conn.close()
        return redirect(url_for('inicio'))
    return render_template('agregar.html', categorias=categorias)

@app.route('/comprar', methods=['GET', 'POST'])
@login_required
def comprar():
    conn = conectar_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        proveedor = request.form.get('proveedor', 'Proveedor General')
        producto_ids = request.form.getlist('producto_id[]')
        costos_unitarios = request.form.getlist('costo_unitario[]')
        cantidades = request.form.getlist('cantidad[]')
        
        for p_id, costo_str, cant_str in zip(producto_ids, costos_unitarios, cantidades):
            if p_id and cant_str and costo_str:
                cant = int(cant_str)
                costo_u = float(costo_str)
                if cant > 0:
                    cursor.execute("SELECT nombre, color, stock_actual FROM productos WHERE id = %s", (p_id,))
                    prod = cursor.fetchone()
                    if prod:
                        costo_total = costo_u * cant
                        nuevo_stock = prod['stock_actual'] + cant
                        nombre_completo = f"{prod['nombre']} ({prod['color']})"
                        
                        cursor.execute("""INSERT INTO historial_compras (producto_id, producto_nombre, proveedor, costo_unitario, cantidad, costo_total) VALUES (%s, %s, %s, %s, %s, %s)""", (p_id, nombre_completo, proveedor, costo_u, cant, costo_total))
                        cursor.execute("UPDATE productos SET stock_actual = %s WHERE id = %s", (nuevo_stock, p_id))
        
        conn.commit()
        conn.close()
        return redirect(url_for('historial_compras'))

    cursor.execute("SELECT id, nombre, color, categoria FROM productos ORDER BY nombre ASC")
    productos = cursor.fetchall()
    conn.close()
    return render_template('comprar.html', productos=productos)

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    categorias = ['Flexiplack', 'Cuñete', 'Galón', 'Herramientas', 'Otros']
    conn = conectar_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        categoria = request.form['categoria']
        nombre = request.form['nombre']
        color = request.form['color']
        precio = request.form['precio']
        stock_actual = request.form['stock_actual']
        stock_minimo = request.form['stock_minimo']
        cursor.execute('''UPDATE productos SET categoria = %s, nombre = %s, color = %s, precio = %s, stock_actual = %s, stock_minimo = %s WHERE id = %s''', (categoria, nombre, color, precio, stock_actual, stock_minimo, id))
        conn.commit()
        conn.close()
        return redirect(url_for('inicio'))
    cursor.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cursor.fetchone()
    conn.close()
    return render_template('editar.html', producto=producto, categorias=categorias)

@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('inicio'))
@app.route('/vender/<int:id>', methods=['GET', 'POST'])
@login_required
def vender(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE id = %s", (id,))
    prod = cursor.fetchone()
    
    if request.method == 'POST':
        cantidad = int(request.form['cantidad'])
        comprador = request.form['comprador']
        metodo_pago = request.form['metodo_pago']
        if prod and prod['stock_actual'] >= cantidad:
            nuevo_stock = prod['stock_actual'] - cantidad
            total = prod['precio'] * cantidad
            cursor.execute("UPDATE productos SET stock_actual = %s WHERE id = %s", (nuevo_stock, id))
            cursor.execute("""INSERT INTO historial_ventas (producto_nombre, precio, comprador, metodo_pago, cantidad, total) VALUES (%s, %s, %s, %s, %s, %s)""", (f"{prod['nombre']} ({prod['color']})", prod['precio'], comprador, metodo_pago, cantidad, total))
            conn.commit()
            conn.close()
            return redirect(url_for('inicio'))
    conn.close()
    return render_template('vender.html', producto=prod)

@app.route('/caja')
@login_required
def caja():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""SELECT metodo_pago, SUM(total) as total_metodo, COUNT(*) as cantidad_transacciones FROM historial_ventas WHERE DATE(fecha) = CURRENT_DATE GROUP BY metodo_pago""")
    resumen_metodos = cursor.fetchall()
    
    cursor.execute("""SELECT SUM(total) as total_dia FROM historial_ventas WHERE DATE(fecha) = CURRENT_DATE""")
    res_total = cursor.fetchone()
    total_dia = res_total['total_dia'] if res_total and res_total['total_dia'] else 0.0
    
    cursor.execute("""SELECT * FROM historial_ventas WHERE DATE(fecha) = CURRENT_DATE ORDER BY id DESC""")
    ventas_hoy = cursor.fetchall()
    conn.close()
    return render_template('caja.html', resumen_metodos=resumen_metodos, total_dia=total_dia, ventas_hoy=ventas_hoy)

@app.route('/historial')
@login_required
def historial():
    conn = conectar_db()
    cursor = conn.cursor()
    # Traemos las ventas y creamos una columna extra solo con la fecha (sin la hora)
    cursor.execute("SELECT *, TO_CHAR(fecha, 'YYYY-MM-DD') as fecha_corta FROM historial_ventas ORDER BY fecha DESC, id DESC")
    ventas_crudas = cursor.fetchall()
    conn.close()

    # Aquí hacemos la magia: agrupamos las ventas por día y sumamos el total
    ventas_por_dia = {}
    for v in ventas_crudas:
        fecha = v['fecha_corta']
        if fecha not in ventas_por_dia:
            ventas_por_dia[fecha] = {'ventas': [], 'total_dia': 0.0}
        ventas_por_dia[fecha]['ventas'].append(v)
        ventas_por_dia[fecha]['total_dia'] += float(v['total'])

    # Le enviamos esta información agrupada al HTML
    return render_template('historial.html', ventas_por_dia=ventas_por_dia)


@app.route('/editar_venta/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_venta(id):
    conn = conectar_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        comprador = request.form['comprador']
        metodo_pago = request.form['metodo_pago']
        cantidad = request.form['cantidad']
        total = request.form['total']
        cursor.execute('''UPDATE historial_ventas SET comprador = %s, metodo_pago = %s, cantidad = %s, total = %s WHERE id = %s''', (comprador, metodo_pago, cantidad, total, id))
        conn.commit()
        conn.close()
        return redirect(url_for('historial'))
    cursor.execute("SELECT * FROM historial_ventas WHERE id = %s", (id,))
    venta = cursor.fetchone()
    conn.close()
    return render_template('editar_venta.html', venta=venta)

@app.route('/eliminar_venta/<int:id>')
@login_required
def eliminar_venta(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM historial_ventas WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('historial'))

@app.route('/limpiar_historial')
@login_required
def limpiar_historial():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM historial_ventas")
    conn.commit()
    conn.close()
    return redirect(url_for('historial'))

@app.route('/ticket/<int:id>')
@login_required
def ticket(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT *, TO_CHAR(fecha, 'YYYY-MM-DD HH24:MI:SS') as fecha_formateada FROM historial_ventas WHERE id = %s", (id,))
    venta = cursor.fetchone()
    conn.close()
    if venta:
        return render_template('ticket.html', venta=venta)
    return redirect(url_for('historial'))

@app.route('/exportar')
@login_required
def exportar():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Categoria', 'Nombre', 'Color', 'Precio', 'Stock Actual', 'Stock Minimo'])
    for p in productos:
        writer.writerow([p['id'], p['categoria'], p['nombre'], p['color'], p['precio'], p['stock_actual'], p['stock_minimo']])
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=inventario_pinturas_jam.csv"})

@app.route('/exportar_ventas_dia/<fecha>')
@login_required
def exportar_ventas_dia(fecha):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, TO_CHAR(fecha, 'YYYY-MM-DD HH24:MI:SS') as fecha_texto, comprador, producto_nombre, cantidad, metodo_pago, total FROM historial_ventas WHERE DATE(fecha) = CAST(%s AS DATE) ORDER BY id ASC", (fecha,))
    ventas = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Recibo #', 'Fecha y Hora', 'Comprador', 'Producto', 'Cantidad', 'Metodo de Pago', 'Total ($)'])
    total_dia = 0.0
    for v in ventas:
        writer.writerow([v['id'], v['fecha_texto'], v['comprador'], v['producto_nombre'], v['cantidad'], v['metodo_pago'], v['total']])
        total_dia += float(v['total'])
    writer.writerow([])
    writer.writerow(['', '', '', '', '', 'TOTAL DEL DIA:', f'${total_dia:.2f}'])
    output.seek(0)
    return Response(output.getvalue().encode('utf-8-sig'), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=Cierre_Caja_{fecha}.csv"})
    
@app.route('/historial_compras')
@login_required
def historial_compras():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT *, TO_CHAR(fecha, 'YYYY-MM-DD HH24:MI:SS') as fecha_formateada FROM historial_compras ORDER BY id DESC")
    compras = cursor.fetchall()
    conn.close()
    return render_template('historial_compras.html', compras=compras)

@app.route('/reportes')
@login_required
def reportes():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT producto_nombre, SUM(cantidad) as cant_total, SUM(total) as dinero_total FROM historial_ventas GROUP BY producto_nombre ORDER BY cant_total DESC LIMIT 5")
    top_productos = cursor.fetchall()
    
    cursor.execute("SELECT TO_CHAR(fecha, 'YYYY-MM-DD') as dia, SUM(total) as total_dia FROM historial_ventas GROUP BY TO_CHAR(fecha, 'YYYY-MM-DD') ORDER BY dia ASC LIMIT 7")
    ventas_dias = cursor.fetchall()
    
    cursor.execute("SELECT SUM(total) as total FROM historial_ventas")
    res_ventas = cursor.fetchone()
    total_ingresos = res_ventas['total'] if res_ventas and res_ventas['total'] else 0.0
    
    cursor.execute("SELECT SUM(costo_total) as total FROM historial_compras")
    res_compras = cursor.fetchone()
    total_inversion = res_compras['total'] if res_compras and res_compras['total'] else 0.0
    
    ganancia_estimada = float(total_ingresos) - float(total_inversion)
    conn.close()
    return render_template('reportes.html', top_productos=top_productos, ventas_dias=ventas_dias, total_ingresos=total_ingresos, total_inversion=total_inversion, ganancia_estimada=ganancia_estimada)

@app.route('/cotizar', methods=['GET', 'POST'])
@login_required
def cotizar():
    conn = conectar_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        cliente = request.form.get('cliente', 'Cliente Estimado')
        metodo_pago = request.form.get('metodo_pago', 'Efectivo')
        accion = request.form.get('accion', 'cotizar')
        producto_ids = request.form.getlist('producto_id[]')
        cantidades = request.form.getlist('cantidad[]')
        
        items = []
        subtotal = 0.0
        
        for p_id, cant_str in zip(producto_ids, cantidades):
            if p_id and cant_str:
                cant = int(cant_str)
                if cant > 0:
                    cursor.execute("SELECT id, nombre, color, precio, stock_actual FROM productos WHERE id = %s", (p_id,))
                    prod = cursor.fetchone()
                    if prod:
                        total_item = float(prod['precio']) * cant
                        subtotal += total_item
                        items.append({
                            'id': prod['id'],
                            'nombre': prod['nombre'],
                            'color': prod['color'],
                            'precio': float(prod['precio']),
                            'cantidad': cant,
                            'total': total_item
                        })
                        
                        if accion == 'vender':
                            nuevo_stock = prod['stock_actual'] - cant
                            cursor.execute("UPDATE productos SET stock_actual = %s WHERE id = %s", (nuevo_stock, prod['id']))
                            cursor.execute("""INSERT INTO historial_ventas (producto_nombre, precio, comprador, metodo_pago, cantidad, total) 
                                              VALUES (%s, %s, %s, %s, %s, %s)""", 
                                           (f"{prod['nombre']} ({prod['color']})", prod['precio'], cliente, metodo_pago, cant, total_item))
        
        conn.commit()
        conn.close()
        
        if accion == 'vender':
            return redirect(url_for('historial'))
        else:
            return render_template('cotizacion_imprimir.html', cliente=cliente, items=items, subtotal=subtotal)
            
    cursor.execute("SELECT id, nombre, color, precio, categoria FROM productos ORDER BY nombre ASC")
    productos = cursor.fetchall()
    conn.close()
    return render_template('cotizar.html', productos=productos)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
