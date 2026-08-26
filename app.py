from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'pinturas_jam_secret_key_2026'

DB_NAME = 'pinturas_jam.db'

# Lista oficial de categorías del negocio
CATEGORIAS_PRODUCTOS = [
    "Flexipack",
    "Cuñetes",
    "Galones",
    "Medio Galón",
    "Herramientas",
    "Especiales y Solventes",
    "Otros"
]

def conectar_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_bd():
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Tabla de productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT,
            nombre TEXT NOT NULL,
            color TEXT NOT NULL,
            precio REAL NOT NULL,
            stock_actual INTEGER NOT NULL,
            stock_minimo INTEGER NOT NULL
        )
    ''')
    
    # Tabla de ventas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            nombre_producto TEXT,
            color TEXT,
            cantidad INTEGER,
            precio_unitario REAL,
            total REAL,
            comprador TEXT,
            metodo_pago TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cajero TEXT
        )
    ''')

    # Tabla de compras / entradas de inventario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            nombre_producto TEXT,
            proveedor TEXT,
            costo_unitario REAL,
            cantidad INTEGER,
            total REAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario TEXT
        )
    ''')

    # Crear usuario gerente por defecto si no existe
    cursor.execute("SELECT * FROM usuarios WHERE username = 'gerente'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", ('gerente', '1234'))
        
    conn.commit()
    conn.close()

inicializar_bd()

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
        # Robusto: acepta tanto 'username' como 'usuario' de cualquier formulario
        username = request.form.get('username') or request.form.get('usuario')
        password = request.form.get('password') or request.form.get('contrasena')
        
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['usuario'] = user['username']
            return redirect(url_for('inicio'))
        else:
            error = "Usuario o contraseña incorrectos."
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def inicio():
    busqueda = request.args.get('busqueda', '')
    conn = conectar_db()
    cursor = conn.cursor()
    if busqueda:
        cursor.execute("SELECT * FROM productos WHERE nombre LIKE ? OR color LIKE ? OR categoria LIKE ?", (f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%'))
        productos = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()
    
    cursor.execute("SELECT SUM(precio * stock_actual) FROM productos")
    res_total = cursor.fetchone()[0]
    valor_total = res_total if res_total else 0.0
    conn.close()

    productos_agrupados = {cat: [] for cat in CATEGORIAS_PRODUCTOS}
    for p in productos:
        cat = p['categoria']
        if cat in productos_agrupados:
            productos_agrupados[cat].append(p)
        else:
            productos_agrupados["Otros"].append(p)

    return render_template('index.html', productos=productos, productos_agrupados=productos_agrupados, categorias=CATEGORIAS_PRODUCTOS, busqueda=busqueda, valor_total=valor_total)

@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    if request.method == 'POST':
        categoria = request.form['categoria']
        nombre = request.form['nombre']
        color = request.form['color']
        precio = float(request.form['precio'])
        stock_actual = int(request.form['stock_actual'])
        stock_minimo = int(request.form['stock_minimo'])

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO productos (categoria, nombre, color, precio, stock_actual, stock_minimo) VALUES (?, ?, ?, ?, ?, ?)",
                       (categoria, nombre, color, precio, stock_actual, stock_minimo))
        conn.commit()
        conn.close()
        return redirect(url_for('inicio'))
    return render_template('agregar.html', categorias=CATEGORIAS_PRODUCTOS)

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    conn = conectar_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        categoria = request.form['categoria']
        nombre = request.form['nombre']
        color = request.form['color']
        precio = float(request.form['precio'])
        stock_actual = int(request.form['stock_actual'])
        stock_minimo = int(request.form['stock_minimo'])

        cursor.execute("UPDATE productos SET categoria=?, nombre=?, color=?, precio=?, stock_actual=?, stock_minimo=? WHERE id=?",
                       (categoria, nombre, color, precio, stock_actual, stock_minimo, id))
        conn.commit()
        conn.close()
        return redirect(url_for('inicio'))
    
    cursor.execute("SELECT * FROM productos WHERE id = ?", (id,))
    producto = cursor.fetchone()
    conn.close()
    return render_template('editar.html', producto=producto, categorias=CATEGORIAS_PRODUCTOS)

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
    if request.method == 'POST':
        cantidad = int(request.form['cantidad'])
        comprador = request.form['comprador']
        metodo_pago = request.form['metodo_pago']

        cursor.execute("SELECT * FROM productos WHERE id = ?", (id,))
        prod = cursor.fetchone()

        if prod and prod['stock_actual'] >= cantidad:
            nuevo_stock = prod['stock_actual'] - cantidad
            total = prod['precio'] * cantidad
            cajero = session.get('usuario', 'Desconocido')

            cursor.execute("UPDATE productos SET stock_actual = ? WHERE id = ?", (nuevo_stock, id))
            cursor.execute("INSERT INTO ventas (producto_id, nombre_producto, color, cantidad, precio_unitario, total, comprador, metodo_pago, cajero) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (id, prod['nombre'], prod['color'], cantidad, prod['precio'], total, comprador, metodo_pago, cajero))
            conn.commit()
            conn.close()
            return redirect(url_for('inicio'))
        
    cursor.execute("SELECT * FROM productos WHERE id = ?", (id,))
    producto = cursor.fetchone()
    conn.close()
    return render_template('vender.html', producto=producto)

@app.route('/comprar', methods=['GET', 'POST'])
@login_required
def comprar():
    conn = conectar_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        producto_id = request.form['producto_id']
        proveedor = request.form['proveedor']
        costo_unitario = float(request.form['costo_unitario'])
        cantidad = int(request.form['cantidad'])

        cursor.execute("SELECT * FROM productos WHERE id = ?", (producto_id,))
        prod = cursor.fetchone()

        if prod:
            nuevo_stock = prod['stock_actual'] + cantidad
            total = costo_unitario * cantidad
            usuario = session.get('usuario', 'Desconocido')

            cursor.execute("UPDATE productos SET stock_actual = ? WHERE id = ?", (nuevo_stock, producto_id))
            cursor.execute("INSERT INTO compras (producto_id, nombre_producto, proveedor, costo_unitario, cantidad, total, usuario) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (producto_id, f"{prod['nombre']} ({prod['color']})", proveedor, costo_unitario, cantidad, total, usuario))
            conn.commit()
            conn.close()
            return redirect(url_for('historial_compras'))

    cursor.execute("SELECT id, categoria, nombre, color, precio FROM productos ORDER BY nombre ASC")
    productos = cursor.fetchall()
    conn.close()
    return render_template('comprar.html', productos=productos)

@app.route('/historial_compras')
@login_required
def historial_compras():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM compras ORDER BY fecha DESC")
    compras = cursor.fetchall()
    conn.close()
    return render_template('historial_compras.html', compras=compras)

@app.route('/historial')
@login_required
def historial():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ventas ORDER BY fecha DESC")
    ventas = cursor.fetchall()
    conn.close()
    return render_template('historial.html', ventas=ventas)

@app.route('/cotizar', methods=['GET', 'POST'])
@login_required
def cotizar():
    conn = conectar_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        cliente = request.form.get('cliente', 'Cliente Estimado')
        metodo_pago = request.form.get('metodo_pago', 'Efectivo')
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
        return render_template('cotizacion_imprimir.html', cliente=cliente, metodo_pago=metodo_pago, items=items, subtotal=subtotal)
    
    cursor.execute("SELECT id, categoria, nombre, color, precio FROM productos ORDER BY nombre ASC")
    productos = cursor.fetchall()
    conn.close()
    return render_template('cotizar.html', productos=productos)

@app.route('/caja')
@login_required
def caja():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ventas WHERE DATE(fecha) = DATE('now', 'localtime')")
    ventas_hoy = cursor.fetchall()
    total_caja = sum(v['total'] for v in ventas_hoy)
    conn.close()
    return render_template('caja.html', ventas_hoy=ventas_hoy, total_caja=total_caja)

@app.route('/reportes')
@login_required
def reportes():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total) FROM ventas")
    total_ventas_historico = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT COUNT(*) FROM ventas")
    num_ventas = cursor.fetchone()[0] or 0
    conn.close()
    return render_template('reportes.html', total_ventas_historico=total_ventas_historico, num_ventas=num_ventas)

@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
def usuarios():
    if session.get('usuario') != 'gerente':
        return redirect(url_for('inicio'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        nuevo_user = request.form['username']
        nuevo_pass = request.form['password']
        try:
            cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", (nuevo_user, nuevo_pass))
            conn.commit()
        except:
            pass
    cursor.execute("SELECT id, username FROM usuarios")
    lista_usuarios = cursor.fetchall()
    conn.close()
    return render_template('usuarios.html', usuarios=lista_usuarios)

if __name__ == '__main__':
    app.run(debug=True)
