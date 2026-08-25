from flask import Flask, render_template, request, redirect, url_for, Response, session
from functools import wraps
import sqlite3
import csv
import io

app = Flask(__name__)
app.secret_key = 'J4m_P1ntur4s#2026!k9$mX8zQ2Lp_SecureKey'

def conectar_db():
    conn = sqlite3.connect('pinturas_jam.db')
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Tabla productos
    cursor.execute('''CREATE TABLE IF NOT EXISTS productos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, color TEXT NOT NULL, precio REAL NOT NULL, stock_actual INTEGER NOT NULL, stock_minimo INTEGER NOT NULL)''')
    try: cursor.execute("ALTER TABLE productos ADD COLUMN categoria TEXT DEFAULT 'Pinturas y Acabados'")
    except: pass
    
    # Tabla historial ventas
    cursor.execute('''CREATE TABLE IF NOT EXISTS historial_ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, producto_nombre TEXT NOT NULL, precio REAL NOT NULL, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    try: cursor.execute("ALTER TABLE historial_ventas ADD COLUMN comprador TEXT DEFAULT 'Consumidor Final'")
    except: pass
    try: cursor.execute("ALTER TABLE historial_ventas ADD COLUMN metodo_pago TEXT DEFAULT 'Efectivo'")
    except: pass
    try: cursor.execute("ALTER TABLE historial_ventas ADD COLUMN cantidad INTEGER DEFAULT 1")
    except: pass
    try: cursor.execute("ALTER TABLE historial_ventas ADD COLUMN total REAL DEFAULT 0.0")
    except: pass
    
    # Tabla historial compras
    cursor.execute('''CREATE TABLE IF NOT EXISTS historial_compras (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        producto_id INTEGER NOT NULL,
                        producto_nombre TEXT NOT NULL,
                        proveedor TEXT NOT NULL, 
                        costo_unitario REAL NOT NULL, 
                        cantidad INTEGER NOT NULL, 
                        costo_total REAL NOT NULL, 
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # --- TABLA DE USUARIOS WEB ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL)''')
    
    # Crear usuarios por defecto si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", ("gerente", "G3r3nt3#JAM.2026!x9"))
        cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", ("suegra", "Adm1n_JAM#9876!z"))
        
    conn.commit()
    conn.close()

inicializar_db()

# --- SISTEMA DE LOGIN ---
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
        cursor.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (usuario, password))
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

# --- GESTIÓN DE USUARIOS (Solo Gerente) ---
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
        
        cursor.execute("SELECT * FROM usuarios WHERE username = ?", (nuevo_user,))
        existe = cursor.fetchone()
        
        if existe:
            cursor.execute("UPDATE usuarios SET password = ? WHERE username = ?", (nueva_pass, nuevo_user))
        else:
            cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", (nuevo_user, nueva_pass))
            
        conn.commit()
        conn.close()
        return redirect(url_for('usuarios'))
        
    cursor.execute("SELECT * FROM usuarios")
    lista_usuarios = cursor.fetchall()
    conn.close()
    return render_template('usuarios.html', lista_usuarios=lista_usuarios)

# --- RUTAS PROTEGIDAS ---

@app.route('/')
@login_required
def inicio():
    busqueda = request.args.get('busqueda', '')
    conn = conectar_db()
    cursor = conn.cursor()
    if busqueda:
        cursor.execute("SELECT * FROM productos WHERE nombre LIKE ? OR color LIKE ? OR categoria LIKE ?", (f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%'))
    else:
        cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    cursor.execute("SELECT SUM(precio * stock_actual) FROM productos")
    resultado_total = cursor.fetchone()[0]
    valor_total = resultado_total if resultado_total else 0.0
    conn.close()
    return render_template('index.html', productos=productos, busqueda=busqueda, valor_total=valor_total)

@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    if request.method == 'POST':
        categoria = request.form['categoria']
        nombre = request.form['nombre']
        color = request.form['color']
        precio = request.form['precio']
        stock_actual = request.form['stock_actual']
        stock_minimo = request.form['stock_minimo']
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO productos (categoria, nombre, color, precio, stock_actual, stock_minimo) VALUES (?, ?, ?, ?, ?, ?)", (categoria, nombre, color, precio, stock_actual, stock_minimo))
        conn.commit()
        conn.close()
        return redirect(url_for('inicio'))
    return render_template('agregar.html')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    conn = conectar_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        categoria = request.form['categoria']
        nombre = request.form['nombre']
        color = request.form['color']
        precio = request.form['precio']
        stock_actual = request.form['stock_actual']
        stock_minimo = request.form['stock_minimo']
        cursor.execute('''UPDATE productos SET categoria = ?, nombre = ?, color = ?, precio = ?, stock_actual = ?, stock_minimo = ? WHERE id = ?''', (categoria, nombre, color, precio, stock_actual, stock_minimo, id))
        conn.commit()
        conn.close()
        return redirect(url_for('inicio'))
    cursor.execute("SELECT * FROM productos WHERE id = ?", (id,))
    producto = cursor.fetchone()
    conn.close()
    return render_template('editar.html', producto=producto)

@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('inicio'))

@app.route('/vender/<int:id>', methods=['GET', 'POST'])
@login_required
def vender(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE id = ?", (id,))
    prod = cursor.fetchone()
    if request.method == 'POST':
        cantidad = int(request.form['cantidad'])
        comprador = request.form['comprador']
        metodo_pago = request.form['metodo_pago']
        if prod and prod['stock_actual'] >= cantidad:
            nuevo_stock = prod['stock_actual'] - cantidad
            total = prod['precio'] * cantidad
            cursor.execute("UPDATE productos SET stock_actual = ? WHERE id = ?", (nuevo_stock, id))
            cursor.execute("""INSERT INTO historial_ventas (producto_nombre, precio, comprador, metodo_pago, cantidad, total) VALUES (?, ?, ?, ?, ?, ?)""", (prod['nombre'], prod['precio'], comprador, metodo_pago, cantidad, total))
            conn.commit()
            conn.close()
            return redirect(url_for('inicio'))
    conn.close()
    return render_template('vender.html', producto=prod)

@app.route('/comprar', methods=['GET', 'POST'])
@login_required
def comprar():
    conn = conectar_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        producto_id = int(request.form['producto_id'])
        proveedor = request.form['proveedor']
        costo_unitario = float(request.form['costo_unitario'])
        cantidad = int(request.form['cantidad'])
        costo_total = costo_unitario * cantidad
        
        cursor.execute("SELECT nombre, stock_actual FROM productos WHERE id = ?", (producto_id,))
        prod = cursor.fetchone()
        if prod:
            producto_nombre = prod['nombre']
            nuevo_stock = prod['stock_actual'] + cantidad
            cursor.execute("""INSERT INTO historial_compras (producto_id, producto_nombre, proveedor, costo_unitario, cantidad, costo_total) VALUES (?, ?, ?, ?, ?, ?)""", (producto_id, producto_nombre, proveedor, costo_unitario, cantidad, costo_total))
            cursor.execute("UPDATE productos SET stock_actual = ? WHERE id = ?", (nuevo_stock, producto_id))
            conn.commit()
            conn.close()
            return redirect(url_for('inicio'))
    cursor.execute("SELECT id, nombre, color FROM productos ORDER BY nombre ASC")
    productos = cursor.fetchall()
    conn.close()
    return render_template('comprar.html', productos=productos)

@app.route('/caja')
@login_required
def caja():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""SELECT metodo_pago, SUM(total) as total_metodo, COUNT(*) as cantidad_transacciones FROM historial_ventas WHERE DATE(fecha) = DATE('now', 'localtime') GROUP BY metodo_pago""")
    resumen_metodos = cursor.fetchall()
    cursor.execute("""SELECT SUM(total) FROM historial_ventas WHERE DATE(fecha) = DATE('now', 'localtime')""")
    res_total = cursor.fetchone()[0]
    total_dia = res_total if res_total else 0.0
    cursor.execute("""SELECT * FROM historial_ventas WHERE DATE(fecha) = DATE('now', 'localtime') ORDER BY id DESC""")
    ventas_hoy = cursor.fetchall()
    conn.close()
    return render_template('caja.html', resumen_metodos=resumen_metodos, total_dia=total_dia, ventas_hoy=ventas_hoy)

@app.route('/historial')
@login_required
def historial():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT *, DATE(fecha) as fecha_corta FROM historial_ventas ORDER BY id DESC")
    ventas_crudas = cursor.fetchall()
    conn.close()

    ventas_por_dia = {}
    for v in ventas_crudas:
        fecha = v['fecha_corta']
        if fecha not in ventas_por_dia:
            ventas_por_dia[fecha] = {'ventas': [], 'total_dia': 0.0}
        ventas_por_dia[fecha]['ventas'].append(v)
        ventas_por_dia[fecha]['total_dia'] += v['total']

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
        cursor.execute('''UPDATE historial_ventas SET comprador = ?, metodo_pago = ?, cantidad = ?, total = ? WHERE id = ?''', (comprador, metodo_pago, cantidad, total, id))
        conn.commit()
        conn.close()
        return redirect(url_for('historial'))
    cursor.execute("SELECT * FROM historial_ventas WHERE id = ?", (id,))
    venta = cursor.fetchone()
    conn.close()
    return render_template('editar_venta.html', venta=venta)

@app.route('/eliminar_venta/<int:id>')
@login_required
def eliminar_venta(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM historial_ventas WHERE id = ?", (id,))
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
    cursor.execute("SELECT * FROM historial_ventas WHERE id = ?", (id,))
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
    cursor.execute("SELECT * FROM historial_ventas WHERE DATE(fecha) = ? ORDER BY id ASC", (fecha,))
    ventas = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Recibo #', 'Fecha y Hora', 'Comprador', 'Producto', 'Cantidad', 'Metodo de Pago', 'Total ($)'])
    total_dia = 0.0
    for v in ventas:
        writer.writerow([v['id'], v['fecha'], v['comprador'], v['producto_nombre'], v['cantidad'], v['metodo_pago'], v['total']])
        total_dia += v['total']
    writer.writerow([])
    writer.writerow(['', '', '', '', '', 'TOTAL DEL DIA:', f'${total_dia:.2f}'])
    output.seek(0)
    return Response(output.getvalue().encode('utf-8-sig'), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=Cierre_Caja_{fecha}.csv"})
    
@app.route('/historial_compras')
@login_required
def historial_compras():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM historial_compras ORDER BY id DESC")
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
    cursor.execute("SELECT DATE(fecha) as dia, SUM(total) as total_dia FROM historial_ventas GROUP BY DATE(fecha) ORDER BY dia ASC LIMIT 7")
    ventas_dias = cursor.fetchall()
    cursor.execute("SELECT SUM(total) FROM historial_ventas")
    res_ventas = cursor.fetchone()[0]
    total_ingresos = res_ventas if res_ventas else 0.0
    cursor.execute("SELECT SUM(costo_total) FROM historial_compras")
    res_compras = cursor.fetchone()[0]
    total_inversion = res_compras if res_compras else 0.0
    ganancia_estimada = total_ingresos - total_inversion
    conn.close()
    return render_template('reportes.html', top_productos=top_productos, ventas_dias=ventas_dias, total_ingresos=total_ingresos, total_inversion=total_inversion, ganancia_estimada=ganancia_estimada)

@app.route('/cotizar', methods=['GET', 'POST'])
@login_required
def cotizar():
    conn = conectar_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        cliente = request.form.get('cliente', 'Cliente Estimado')
        producto_ids = request.form.getlist('producto_id[]')
        cantidades = request.form.getlist('cantidad[]')
        items = []
        subtotal = 0.0
        for p_id, cant_str in zip(producto_ids, cantidades):
            if p_id and cant_str:
                cant = int(cant_str)
                if cant > 0:
                    cursor.execute("SELECT nombre, color, precio FROM productos WHERE id = ?", (p_id,))
                    prod = cursor.fetchone()
                    if prod:
                        total_item = prod['precio'] * cant
                        subtotal += total_item
                        items.append({'nombre': prod['nombre'], 'color': prod['color'], 'precio': prod['precio'], 'cantidad': cant, 'total': total_item})
        conn.close()
        return render_template('cotizacion_imprimir.html', cliente=cliente, items=items, subtotal=subtotal)
    cursor.execute("SELECT id, nombre, color, precio FROM productos ORDER BY nombre ASC")
    productos = cursor.fetchall()
    conn.close()
    return render_template('cotizar.html', productos=productos)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)