import os
import logging
from functools import wraps
from datetime import datetime

import bcrypt
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql
from pymysql.cursors import DictCursor

# ─── Password helpers ─────────────────────────────────────────────────────────

def _check_password(plain, stored):
    if stored.startswith("$2b$") or stored.startswith("$2a$"):
        try:
            return bcrypt.checkpw(plain.encode(), stored.encode())
        except Exception:
            return False
    return plain == stored

def _hash_password(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ─── App ──────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'logicarga_secret_key')

# ── Filtro Jinja2: fechas en español ──────────────────────────────────
_MESES_ES = ['enero','febrero','marzo','abril','mayo','junio',
              'julio','agosto','septiembre','octubre','noviembre','diciembre']
_DIAS_ES  = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo']

def fecha_es(value, formato='corto'):
    """
    Convierte un objeto datetime/date a texto en español.
    formato='corto'  → '20/03/2026'
    formato='largo'  → '20 de marzo de 2026'
    formato='hora'   → '20/03/2026 14:35'
    formato='larga_hora' → '20 de marzo de 2026, 14:35'
    """
    if not value:
        return '—'
    try:
        d = value
        mes  = _MESES_ES[d.month - 1]
        if formato == 'largo':
            return f"{d.day} de {mes} de {d.year}"
        elif formato == 'hora':
            return f"{d.day:02d}/{d.month:02d}/{d.year} {d.hour:02d}:{d.minute:02d}"
        elif formato == 'larga_hora':
            return f"{d.day} de {mes} de {d.year}, {d.hour:02d}:{d.minute:02d}"
        else:  # corto
            return f"{d.day:02d}/{d.month:02d}/{d.year}"
    except Exception:
        return str(value)

app.jinja_env.filters['fecha_es'] = fecha_es
# ─────────────────────────────────────────────────────────────────────

DB_CONFIG = {
    'host':         os.getenv('MYSQL_HOST', '127.0.0.1'),
    'port':         int(os.getenv('MYSQL_PORT', '3306')),
    'user':         os.getenv('MYSQL_USER', 'root'),
    'password':     os.getenv('MYSQL_PASSWORD', '0000'),
    'database':     os.getenv('MYSQL_DB', 'logicarga_db'),
    'cursorclass':  DictCursor,
    'autocommit':   True,
    'connect_timeout':   5,
    'read_timeout':     30,
    'write_timeout':    30,
    'charset':      'utf8mb4',
}

ROLE_PERMISSIONS = {
    # Administrador: crea usuarios (supervisores y conductores) y gestiona la flota de vehiculos
    'Administrador': {
        'dashboard', 'usuarios', 'supervisores', 'vehiculos', 'viaticos', 'reportes', 'consultas', 'metodologia'
    },
    # Supervisor: monitorea la operacion — ve viajes, conductores, viaticos, reportes, mantenimientos y consultas
    'Supervisor': {
        'dashboard', 'viajes', 'conductores', 'viaticos', 'mantenimientos', 'reportes', 'consultas'
    },
    # Conductor: registra todo lo que ocurre en ruta
    'Conductor': {'dashboard', 'mis_viajes', 'combustible', 'viaticos', 'incidentes'},
}

# ─── DB helpers ───────────────────────────────────────────────────────────────

def get_connection():
    """Abre una conexión a MySQL. Lanza excepción si falla."""
    try:
        return pymysql.connect(**DB_CONFIG)
    except pymysql.OperationalError as e:
        logger.error("No se pudo conectar a la BD: %s", e)
        raise


def check_db() -> bool:
    """Prueba rápida de conectividad. Devuelve True si la BD responde."""
    try:
        con = get_connection()
        with con.cursor() as cur:
            cur.execute("SELECT 1")
        con.close()
        return True
    except Exception as e:
        logger.warning("check_db falló: %s", e)
        return False


def fetch_all(query, params=None):
    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchall()
    except pymysql.Error as e:
        logger.error("fetch_all error — query: %s | params: %s | err: %s", query, params, e)
        raise
    finally:
        con.close()


def fetch_one(query, params=None):
    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchone()
    except pymysql.Error as e:
        logger.error("fetch_one error — query: %s | params: %s | err: %s", query, params, e)
        raise
    finally:
        con.close()


def execute_query(query, params=None):
    con = get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(query, params or ())
            return cur.lastrowid
    except pymysql.Error as e:
        logger.error("execute_query error — query: %s | params: %s | err: %s", query, params, e)
        raise
    finally:
        con.close()


# ─── Auth helpers ──────────────────────────────────────────────────────────────

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    user = session.get('user')
    permissions = ROLE_PERMISSIONS.get(user['rol'], set()) if user else set()
    return {
        'current_user': user,
        'permissions':  permissions,
        'current_year': datetime.now().year,
    }


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('welcome'))


@app.route('/bienvenida')
def welcome():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('welcome.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo   = request.form.get('correo', '').strip()
        password = request.form.get('password', '')

        if not correo or not password:
            flash('Por favor completa todos los campos.', 'error')
            return render_template('login.html', db_ok=check_db())

        try:
            # Check if user exists at all (regardless of activo)
            user_any = fetch_one(
                """
                SELECT u.id, u.nombre, u.correo, u.password,
                       r.nombre AS rol, c.id AS conductor_id, u.activo
                FROM   usuarios u
                INNER  JOIN roles r ON r.id = u.rol_id
                LEFT   JOIN conductores c ON c.usuario_id = u.id
                WHERE  u.correo = %s
                """,
                (correo,),
            )
        except Exception:
            flash('Error de conexión con la base de datos. Intenta de nuevo.', 'error')
            return render_template('login.html', db_ok=False)

        if user_any and _check_password(password, user_any['password']):
            if not user_any['activo']:
                flash('CUENTA_DESACTIVADA', 'desactivada')
                return render_template('login.html', db_ok=check_db())
            session['user'] = {
                'id':           user_any['id'],
                'nombre':       user_any['nombre'],
                'correo':       user_any['correo'],
                'rol':          user_any['rol'],
                'conductor_id': user_any['conductor_id'],
            }
            logger.info("Login exitoso: %s (%s)", user_any['correo'], user_any['rol'])
            return redirect(url_for('dashboard'))

        flash('Correo o contraseña incorrectos.', 'error')

    return render_template('login.html', db_ok=check_db())


@app.route('/logout')
def logout():
    user = session.get('user', {})
    logger.info("Logout: %s", user.get('correo', 'desconocido'))
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    user = session['user']
    conductor_id = user.get('conductor_id')
    is_conductor = user['rol'] == 'Conductor'

    try:
        if is_conductor and conductor_id:
            stats = {
                'vehiculos':   fetch_one('SELECT COUNT(DISTINCT vehiculo_id) AS total FROM viajes WHERE conductor_id=%s', (conductor_id,))['total'],
                'viajes':      fetch_one('SELECT COUNT(*) AS total FROM viajes WHERE conductor_id=%s', (conductor_id,))['total'],
                'incidentes':  fetch_one('SELECT COUNT(*) AS total FROM incidentes WHERE conductor_id=%s', (conductor_id,))['total'],
                'combustible': fetch_one('SELECT COALESCE(ROUND(SUM(costo_total),0),0) AS total FROM combustible WHERE conductor_id=%s', (conductor_id,))['total'],
                'viaticos':    fetch_one('SELECT COALESCE(ROUND(SUM(valor_gasto),0),0) AS total FROM viaticos WHERE conductor_id=%s', (conductor_id,))['total'],
            }
            ultimos_viajes = fetch_all(
                """
                SELECT v.id, v.ciudad_origen, v.ciudad_destino, v.fecha_salida, v.estado,
                       ve.placa, c.nombre_completo AS conductor
                FROM   viajes v
                INNER  JOIN vehiculos ve ON ve.id = v.vehiculo_id
                INNER  JOIN conductores c ON c.id = v.conductor_id
                WHERE  v.conductor_id = %s
                ORDER  BY v.id DESC LIMIT 5
                """,
                (conductor_id,)
            )
            viajes_mes = fetch_all(
                """
                SELECT DATE_FORMAT(fecha_salida,'%%Y-%%m') AS mes,
                       COUNT(*) AS total,
                       SUM(CASE WHEN estado='Finalizado' THEN 1 ELSE 0 END) AS finalizados
                FROM viajes WHERE conductor_id=%s
                GROUP BY mes ORDER BY mes DESC LIMIT 6
                """,
                (conductor_id,)
            )
            combustible_mes = fetch_all(
                """
                SELECT DATE_FORMAT(fecha_registro,'%%Y-%%m') AS mes,
                       ROUND(SUM(costo_total),0) AS costo,
                       ROUND(SUM(litros),1) AS litros
                FROM combustible WHERE conductor_id=%s
                GROUP BY mes ORDER BY mes DESC LIMIT 6
                """,
                (conductor_id,)
            )
            incidentes_tipo = fetch_all(
                """
                SELECT tipo_incidente, COUNT(*) AS total
                FROM incidentes WHERE conductor_id=%s
                GROUP BY tipo_incidente ORDER BY total DESC
                """,
                (conductor_id,)
            )
            viaje_activo = fetch_one(
                """
                SELECT v.id, v.ciudad_origen, v.ciudad_destino, v.fecha_salida, v.estado, ve.placa
                FROM viajes v INNER JOIN vehiculos ve ON ve.id = v.vehiculo_id
                WHERE v.conductor_id=%s AND v.estado IN ('En ruta','Programado')
                ORDER BY v.id DESC LIMIT 1
                """,
                (conductor_id,)
            )
            alertas = []
        else:
            stats = {
                'vehiculos':   fetch_one('SELECT COUNT(*) AS total FROM vehiculos')['total'],
                'conductores': fetch_one('SELECT COUNT(*) AS total FROM conductores')['total'],
                'viajes':      fetch_one('SELECT COUNT(*) AS total FROM viajes')['total'],
                'incidentes':  fetch_one('SELECT COUNT(*) AS total FROM incidentes')['total'],
            }
            ultimos_viajes = fetch_all(
                """
                SELECT v.id, v.ciudad_origen, v.ciudad_destino, v.fecha_salida, v.estado,
                       ve.placa, c.nombre_completo AS conductor
                FROM   viajes v
                INNER  JOIN vehiculos ve ON ve.id = v.vehiculo_id
                INNER  JOIN conductores c ON c.id = v.conductor_id
                ORDER  BY v.id DESC LIMIT 5
                """
            )
            alertas = fetch_all(
                """
                SELECT ve.placa, ve.kilometraje_actual, m.kilometraje_programado, m.estado,
                       m.descripcion, m.tipo_mantenimiento,
                       (ve.kilometraje_actual - COALESCE(
                           (SELECT MAX(m2.kilometraje_programado) FROM mantenimientos m2
                            WHERE m2.vehiculo_id = ve.id AND m2.estado = 'Completado'), 0
                       )) AS km_desde_ultimo_mant
                FROM   mantenimientos m
                INNER  JOIN vehiculos ve ON ve.id = m.vehiculo_id
                WHERE  m.estado IN ('Pendiente', 'Programado')
                ORDER  BY m.estado ASC, m.kilometraje_programado ASC LIMIT 8
                """
            )
            viajes_mes = fetch_all(
                """
                SELECT DATE_FORMAT(fecha_salida,'%%Y-%%m') AS mes,
                       COUNT(*) AS total,
                       SUM(CASE WHEN estado='Finalizado' THEN 1 ELSE 0 END) AS finalizados
                FROM viajes GROUP BY mes ORDER BY mes DESC LIMIT 6
                """
            )
            combustible_mes = fetch_all(
                """
                SELECT DATE_FORMAT(fecha_registro,'%%Y-%%m') AS mes,
                       ROUND(SUM(costo_total),0) AS costo,
                       ROUND(SUM(litros),1) AS litros
                FROM combustible GROUP BY mes ORDER BY mes DESC LIMIT 6
                """
            )
            incidentes_tipo = fetch_all(
                """
                SELECT tipo_incidente, COUNT(*) AS total
                FROM incidentes GROUP BY tipo_incidente ORDER BY total DESC
                """
            )
            viaje_activo = None

    except Exception as e:
        flash('Error al cargar el dashboard. Revisa la conexión con la base de datos.', 'error')
        logger.error("dashboard error: %s", e)
        stats, ultimos_viajes, alertas = {}, [], []
        viajes_mes, combustible_mes, incidentes_tipo, viaje_activo = [], [], [], None

    return render_template('dashboard.html', stats=stats,
                           ultimos_viajes=ultimos_viajes, alertas=alertas,
                           viajes_mes=list(reversed(viajes_mes)) if viajes_mes else [],
                           combustible_mes=list(reversed(combustible_mes)) if combustible_mes else [],
                           incidentes_tipo=incidentes_tipo or [],
                           viaje_activo=viaje_activo,
                           is_conductor=is_conductor)


@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
def usuarios():
    if session['user']['rol'] != 'Administrador':
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            logger.info("usuarios POST keys: %s", list(request.form.keys()))
            logger.info("usuarios POST data: %s", dict(request.form))

            rol_id   = request.form.get('rol_id', '').strip()
            nombre   = (request.form.get('nombre') or request.form.get('nombre_conductor', '')).strip()
            correo   = (request.form.get('correo') or request.form.get('correo_conductor', '')).strip()
            password = (request.form.get('password') or request.form.get('password_conductor', '')).strip()
            telefono = (request.form.get('telefono') or request.form.get('telefono_conductor', '')).strip()

            if not rol_id or not nombre or not correo or not password:
                flash(f'Faltan campos: rol={rol_id} nombre={nombre} correo={correo}', 'error')
                return redirect(url_for('usuarios'))

            hashed_pw = _hash_password(password)
            execute_query(
                "INSERT INTO usuarios (rol_id, nombre, correo, password, telefono, activo) VALUES (%s,%s,%s,%s,%s,1)",
                (rol_id, nombre, correo, hashed_pw, telefono)
            )

            rol_conductor    = fetch_all("SELECT id FROM roles WHERE nombre='Conductor' LIMIT 1")
            rol_conductor_id = rol_conductor[0]['id'] if rol_conductor else None

            if str(rol_id) == str(rol_conductor_id):
                nuevo_usuario = fetch_all("SELECT id FROM usuarios WHERE correo=%s LIMIT 1", (correo,))
                if nuevo_usuario:
                    execute_query(
                        """INSERT INTO conductores
                           (usuario_id, nombre_completo, numero_licencia, tipo_licencia,
                            telefono, email, ciudad, fecha_vencimiento_licencia, estado)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (nuevo_usuario[0]['id'], nombre,
                         request.form.get('numero_licencia') or None,
                         request.form.get('tipo_licencia') or None,
                         telefono or None, correo,
                         request.form.get('ciudad_conductor') or None,
                         request.form.get('fecha_vencimiento_licencia') or None,
                         'Activo')
                    )

            flash('Usuario creado correctamente.', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            logger.error("usuarios POST error: %s", e, exc_info=True)
        return redirect(url_for('usuarios'))

    try:
        data  = fetch_all("""SELECT u.id, u.nombre, u.correo, u.telefono, u.activo, r.nombre AS rol, c.numero_licencia, c.tipo_licencia, c.fecha_vencimiento_licencia, c.ciudad, c.direccion FROM usuarios u INNER JOIN roles r ON r.id = u.rol_id LEFT JOIN conductores c ON c.usuario_id = u.id ORDER BY u.id DESC""")
        roles = fetch_all('SELECT * FROM roles ORDER BY id')
    except Exception as e:
        flash('Error al cargar usuarios.', 'error')
        logger.error("usuarios GET error: %s", e)
        data, roles = [], []
    return render_template('usuarios.html', items=data, roles=roles)


@app.route('/conductores', methods=['GET', 'POST'])
@login_required
def conductores():
    if session['user']['rol'] not in ('Administrador', 'Supervisor'):
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            nombre_completo = request.form.get('nombre_completo', '').strip()
            numero_licencia = request.form.get('numero_licencia', '').strip()
            tipo_licencia   = request.form.get('tipo_licencia', '').strip() or None
            telefono        = request.form.get('telefono', '').strip() or None
            email           = request.form.get('email', '').strip() or None
            ciudad          = request.form.get('ciudad', '').strip() or None
            fecha_venc      = request.form.get('fecha_vencimiento_licencia', '').strip() or None
            password        = request.form.get('password', '').strip()
            password_confirm= request.form.get('password_confirm', '').strip()

            # Validaciones de servidor
            import re as _re
            if not nombre_completo:
                flash('El nombre completo es obligatorio.', 'error')
                return redirect(url_for('conductores'))
            if _re.search(r'\d', nombre_completo):
                flash('El nombre no debe contener números.', 'error')
                return redirect(url_for('conductores'))
            if not numero_licencia:
                flash('El número de licencia es obligatorio.', 'error')
                return redirect(url_for('conductores'))
            if not email:
                flash('El correo electrónico es obligatorio.', 'error')
                return redirect(url_for('conductores'))
            if not password:
                flash('La contraseña es obligatoria.', 'error')
                return redirect(url_for('conductores'))
            if len(password) < 8:
                flash('La contraseña debe tener mínimo 8 caracteres.', 'error')
                return redirect(url_for('conductores'))
            if password != password_confirm:
                flash('Las contraseñas no coinciden.', 'error')
                return redirect(url_for('conductores'))

            # Verificar si ya existe un usuario con ese correo
            usuario_existente = fetch_one('SELECT id FROM usuarios WHERE correo = %s', (email,))
            if usuario_existente:
                flash('Ya existe un usuario registrado con ese correo electrónico.', 'error')
                return redirect(url_for('conductores'))

            # Obtener rol_id de Conductor
            rol_conductor = fetch_one("SELECT id FROM roles WHERE nombre='Conductor' LIMIT 1")
            rol_id = rol_conductor['id'] if rol_conductor else None

            # Crear usuario en la tabla usuarios
            hashed_pw = _hash_password(password)
            nuevo_usuario_id = execute_query(
                "INSERT INTO usuarios (rol_id, nombre, correo, password, telefono, activo) VALUES (%s,%s,%s,%s,%s,1)",
                (rol_id, nombre_completo, email, hashed_pw, telefono)
            )

            # Crear el conductor vinculado al usuario
            execute_query(
                """INSERT INTO conductores (usuario_id, nombre_completo, numero_licencia, tipo_licencia,
                   telefono, email, ciudad, fecha_vencimiento_licencia, estado)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (nuevo_usuario_id, nombre_completo, numero_licencia, tipo_licencia,
                 telefono, email, ciudad, fecha_venc, 'Activo')
            )
            flash('Conductor registrado correctamente.', 'success')
        except Exception as e:
            flash('Error al registrar el conductor.', 'error')
            logger.error("conductores POST error: %s", e)
        return redirect(url_for('conductores'))

    try:
        data = fetch_all('SELECT * FROM conductores ORDER BY id DESC')
        usuarios_libres = fetch_all(
            """SELECT u.id, u.nombre FROM usuarios u
               INNER JOIN roles r ON r.id = u.rol_id
               LEFT  JOIN conductores c ON c.usuario_id = u.id
               WHERE r.nombre = 'Conductor' AND c.id IS NULL ORDER BY u.nombre"""
        )
    except Exception as e:
        flash('Error al cargar conductores.', 'error')
        logger.error("conductores GET error: %s", e)
        data, usuarios_libres = [], []
    return render_template('conductores.html', items=data, usuarios_libres=usuarios_libres)




@app.route('/supervisores', methods=['GET', 'POST'])
@login_required
def supervisores():
    if session['user']['rol'] != 'Administrador':
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            nombre_completo  = request.form.get('nombre_completo', '').strip()
            telefono         = request.form.get('telefono', '').strip() or None
            email            = request.form.get('email', '').strip() or None
            ciudad           = request.form.get('ciudad', '').strip() or None
            password         = request.form.get('password', '').strip()
            password_confirm = request.form.get('password_confirm', '').strip()

            import re as _re
            if not nombre_completo:
                flash('El nombre completo es obligatorio.', 'error')
                return redirect(url_for('supervisores'))
            if _re.search(r'\d', nombre_completo):
                flash('El nombre no debe contener numeros.', 'error')
                return redirect(url_for('supervisores'))
            if not email:
                flash('El correo electronico es obligatorio.', 'error')
                return redirect(url_for('supervisores'))
            if not password:
                flash('La contrasena es obligatoria.', 'error')
                return redirect(url_for('supervisores'))
            if len(password) < 8:
                flash('La contrasena debe tener minimo 8 caracteres.', 'error')
                return redirect(url_for('supervisores'))
            if password != password_confirm:
                flash('Las contrasenas no coinciden.', 'error')
                return redirect(url_for('supervisores'))

            usuario_existente = fetch_one('SELECT id FROM usuarios WHERE correo = %s', (email,))
            if usuario_existente:
                flash('Ya existe un usuario registrado con ese correo electronico.', 'error')
                return redirect(url_for('supervisores'))

            rol_supervisor = fetch_one("SELECT id FROM roles WHERE nombre='Supervisor' LIMIT 1")
            rol_id = rol_supervisor['id'] if rol_supervisor else None

            hashed_pw = _hash_password(password)
            execute_query(
                "INSERT INTO usuarios (rol_id, nombre, correo, password, telefono, activo) VALUES (%s,%s,%s,%s,%s,1)",
                (rol_id, nombre_completo, email, hashed_pw, telefono)
            )
            flash('Supervisor registrado correctamente.', 'success')
        except Exception as e:
            flash('Error al registrar el supervisor.', 'error')
            logger.error("supervisores POST error: %s", e)
        return redirect(url_for('supervisores'))

    try:
        data = fetch_all("""
            SELECT u.id, u.nombre, u.correo, u.telefono, u.activo
            FROM usuarios u
            INNER JOIN roles r ON r.id = u.rol_id
            WHERE r.nombre = 'Supervisor'
            ORDER BY u.id DESC
        """)
    except Exception as e:
        flash('Error al cargar supervisores.', 'error')
        logger.error("supervisores GET error: %s", e)
        data = []
    return render_template('supervisores.html', items=data)

@app.route('/vehiculos', methods=['GET', 'POST'])
@login_required
def vehiculos():
    if session['user']['rol'] != 'Administrador':
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            execute_query(
                """INSERT INTO vehiculos (placa, modelo, anio, capacidad_carga, kilometraje_actual, estado, fecha_ultimo_mantenimiento)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (request.form['placa'], request.form['modelo'],
                 request.form['anio'] or None,
                 request.form['capacidad_carga'],
                 request.form['kilometraje_actual'], request.form['estado'],
                 request.form['fecha_ultimo_mantenimiento'] or None)
            )
            flash('Vehículo registrado correctamente.', 'success')
        except Exception as e:
            flash('Error al registrar el vehículo.', 'error')
            logger.error("vehiculos POST error: %s", e)
        return redirect(url_for('vehiculos'))

    try:
        data = fetch_all('SELECT * FROM vehiculos ORDER BY id DESC')
    except Exception as e:
        flash('Error al cargar vehículos.', 'error')
        logger.error("vehiculos GET error: %s", e)
        data = []
    return render_template('vehiculos.html', items=data)


@app.route('/viajes', methods=['GET', 'POST'])
@login_required
def viajes():
    if session['user']['rol'] not in ('Supervisor', 'Administrador'):
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            execute_query(
                """INSERT INTO viajes
                   (vehiculo_id, conductor_id, ciudad_origen, ciudad_destino, fecha_salida, fecha_llegada,
                    tipo_carga, kilometraje_inicio, kilometraje_fin, combustible_inicio, combustible_fin,
                    estado, observaciones)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (request.form['vehiculo_id'], request.form['conductor_id'],
                 request.form['ciudad_origen'], request.form['ciudad_destino'],
                 request.form['fecha_salida'], request.form['fecha_llegada'] or None,
                 request.form['tipo_carga'], request.form['kilometraje_inicio'],
                 request.form['kilometraje_fin'] or None, request.form['combustible_inicio'],
                 request.form['combustible_fin'] or None, request.form['estado'],
                 request.form['observaciones'])
            )
            flash('Viaje registrado correctamente.', 'success')
        except Exception as e:
            flash('Error al registrar el viaje.', 'error')
            logger.error("viajes POST error: %s", e)
        return redirect(url_for('viajes'))

    try:
        data = fetch_all(
            """SELECT v.*, ve.placa, c.nombre_completo AS conductor
               FROM viajes v
               INNER JOIN vehiculos ve ON ve.id = v.vehiculo_id
               INNER JOIN conductores c ON c.id = v.conductor_id
               ORDER BY v.id DESC"""
        )
        vehiculos_data  = fetch_all('SELECT id, placa FROM vehiculos WHERE estado <> "Fuera de servicio" ORDER BY placa')
        conductores_data = fetch_all('SELECT id, nombre_completo FROM conductores WHERE estado = "Activo" ORDER BY nombre_completo')
    except Exception as e:
        flash('Error al cargar viajes.', 'error')
        logger.error("viajes GET error: %s", e)
        data, vehiculos_data, conductores_data = [], [], []
    return render_template('viajes.html', items=data, vehiculos=vehiculos_data, conductores=conductores_data)


@app.route('/mis-viajes')
@login_required
def mis_viajes():
    user = session['user']
    if user['rol'] != 'Conductor' or not user['conductor_id']:
        flash('No tienes viajes asignados.', 'error')
        return redirect(url_for('dashboard'))
    try:
        data = fetch_all(
            """SELECT v.*, ve.placa FROM viajes v
               INNER JOIN vehiculos ve ON ve.id = v.vehiculo_id
               WHERE v.conductor_id = %s ORDER BY v.id DESC""",
            (user['conductor_id'],)
        )
    except Exception as e:
        flash('Error al cargar tus viajes.', 'error')
        logger.error("mis_viajes error: %s", e)
        data = []
    return render_template('mis_viajes.html', items=data)


@app.route('/mis-viajes/iniciar/<int:viaje_id>', methods=['POST'])
@login_required
def iniciar_viaje(viaje_id):
    user = session['user']
    if user['rol'] != 'Conductor' or not user['conductor_id']:
        return jsonify(ok=False, msg='Sin permisos'), 403
    try:
        viaje = fetch_one(
            "SELECT id, estado, conductor_id FROM viajes WHERE id = %s",
            (viaje_id,)
        )
        if not viaje:
            return jsonify(ok=False, msg='Viaje no encontrado'), 404
        if viaje['conductor_id'] != user['conductor_id']:
            return jsonify(ok=False, msg='Este viaje no te pertenece'), 403
        if viaje['estado'] != 'Programado':
            return jsonify(ok=False, msg=f"El viaje ya está en estado: {viaje['estado']}"), 400

        km_inicio    = request.form.get('kilometraje_inicio') or None
        comb_inicio  = request.form.get('combustible_inicio') or None
        fecha_salida = request.form.get('fecha_salida') or None
        observaciones= request.form.get('observaciones') or None

        execute_query(
            """UPDATE viajes
               SET estado = 'En ruta',
                   kilometraje_inicio  = COALESCE(%s, kilometraje_inicio),
                   combustible_inicio  = COALESCE(%s, combustible_inicio),
                   fecha_salida        = COALESCE(%s, fecha_salida),
                   observaciones       = COALESCE(%s, observaciones)
               WHERE id = %s""",
            (km_inicio, comb_inicio, fecha_salida, observaciones, viaje_id)
        )
        return jsonify(ok=True, msg='Viaje iniciado correctamente')
    except Exception as e:
        logger.error("iniciar_viaje error: %s", e)
        return jsonify(ok=False, msg='Error al iniciar el viaje'), 500


@app.route('/mis-viajes/finalizar/<int:viaje_id>', methods=['POST'])
@login_required
def finalizar_viaje(viaje_id):
    user = session['user']
    if user['rol'] != 'Conductor' or not user['conductor_id']:
        return jsonify(ok=False, msg='Sin permisos'), 403
    try:
        # Verify this viaje belongs to this conductor and is En ruta
        viaje = fetch_one(
            "SELECT id, estado, conductor_id FROM viajes WHERE id = %s",
            (viaje_id,)
        )
        if not viaje:
            return jsonify(ok=False, msg='Viaje no encontrado'), 404
        if viaje['conductor_id'] != user['conductor_id']:
            return jsonify(ok=False, msg='Este viaje no te pertenece'), 403
        if viaje['estado'] not in ('En ruta', 'Programado'):
            return jsonify(ok=False, msg=f"El viaje ya está en estado: {viaje['estado']}"), 400

        km_fin       = request.form.get('kilometraje_fin') or None
        comb_fin     = request.form.get('combustible_fin') or None
        fecha_llegada= request.form.get('fecha_llegada')   or None
        observaciones= request.form.get('observaciones')   or None

        execute_query(
            """UPDATE viajes
               SET estado = 'Finalizado',
                   kilometraje_fin   = %s,
                   combustible_fin   = %s,
                   fecha_llegada     = %s,
                   observaciones     = COALESCE(%s, observaciones)
               WHERE id = %s""",
            (km_fin, comb_fin, fecha_llegada, observaciones, viaje_id)
        )

        # ── Actualizar kilometraje del vehículo y generar alerta si corresponde ──
        alerta_mantenimiento = None
        if km_fin:
            try:
                # Obtener vehiculo_id y km del último mantenimiento
                viaje_info = fetch_one(
                    """SELECT v.vehiculo_id, ve.kilometraje_actual,
                              ve.fecha_ultimo_mantenimiento,
                              COALESCE(
                                (SELECT MAX(m.kilometraje_programado)
                                 FROM mantenimientos m
                                 WHERE m.vehiculo_id = v.vehiculo_id
                                   AND m.estado = 'Completado'), 0
                              ) AS km_ultimo_mant
                       FROM viajes v
                       INNER JOIN vehiculos ve ON ve.id = v.vehiculo_id
                       WHERE v.id = %s""",
                    (viaje_id,)
                )
                if viaje_info:
                    vehiculo_id   = viaje_info['vehiculo_id']
                    km_nuevo      = int(km_fin)
                    km_ultimo_mant = int(viaje_info['km_ultimo_mant'] or 0)

                    # Actualizar kilometraje actual del vehículo
                    execute_query(
                        "UPDATE vehiculos SET kilometraje_actual = %s WHERE id = %s AND kilometraje_actual < %s",
                        (km_nuevo, vehiculo_id, km_nuevo)
                    )

                    # Verificar si corresponde alerta de mantenimiento preventivo (30.000 km)
                    km_recorridos_desde_mant = km_nuevo - km_ultimo_mant
                    UMBRAL_KM = 30000
                    if km_recorridos_desde_mant >= UMBRAL_KM:
                        # Revisar si ya existe alerta pendiente/programada para este vehículo
                        alerta_existente = fetch_one(
                            """SELECT id FROM mantenimientos
                               WHERE vehiculo_id = %s AND estado IN ('Pendiente','Programado')
                                 AND tipo_mantenimiento = 'Preventivo'
                               LIMIT 1""",
                            (vehiculo_id,)
                        )
                        if not alerta_existente:
                            execute_query(
                                """INSERT INTO mantenimientos
                                   (vehiculo_id, tipo_mantenimiento, descripcion,
                                    kilometraje_programado, costo, estado)
                                   VALUES (%s, 'Preventivo',
                                    'Alerta automática: el vehículo ha recorrido 30.000 km desde el último mantenimiento. Revisar aceite, filtros y frenos.',
                                    %s, 0, 'Pendiente')""",
                                (vehiculo_id, km_nuevo)
                            )
                        alerta_mantenimiento = True
            except Exception as em:
                logger.warning("No se pudo actualizar kilometraje vehículo: %s", em)

        msg = 'Viaje finalizado correctamente'
        if alerta_mantenimiento:
            msg += ' · ⚠️ Se generó una alerta de mantenimiento preventivo (30.000 km alcanzados)'
        return jsonify(ok=True, msg=msg)
    except Exception as e:
        logger.error("finalizar_viaje error: %s", e)
        return jsonify(ok=False, msg='Error al finalizar el viaje'), 500


@app.route('/combustible', methods=['GET', 'POST'])
@login_required
def combustible():
    user = session['user']
    if user['rol'] not in ('Conductor',):
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            execute_query(
                """INSERT INTO combustible (viaje_id, vehiculo_id, conductor_id, tipo_combustible, litros, costo_total, ciudad, fecha_registro, observaciones)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (request.form['viaje_id'], request.form['vehiculo_id'], request.form['conductor_id'],
                 request.form['tipo_combustible'],
                 request.form['litros'], request.form['costo_total'], request.form['ciudad'],
                 request.form['fecha_registro'], request.form['observaciones'])
            )
            flash('Registro de combustible guardado.', 'success')
        except Exception as e:
            flash('Error al guardar el registro de combustible.', 'error')
            logger.error("combustible POST error: %s", e)
        return redirect(url_for('combustible'))

    where, params = '', ()
    if user['rol'] == 'Conductor' and user['conductor_id']:
        where, params = 'WHERE cb.conductor_id = %s', (user['conductor_id'],)

    try:
        data = fetch_all(
            f"""SELECT cb.*, ve.placa, c.nombre_completo AS conductor, v.ciudad_origen, v.ciudad_destino
                FROM combustible cb
                INNER JOIN vehiculos ve ON ve.id = cb.vehiculo_id
                INNER JOIN conductores c ON c.id = cb.conductor_id
                INNER JOIN viajes v ON v.id = cb.viaje_id
                {where} ORDER BY cb.id DESC""",
            params
        )
        viajes_data      = fetch_all('SELECT id, ciudad_origen, ciudad_destino FROM viajes ORDER BY id DESC')
        vehiculos_data   = fetch_all('SELECT id, placa FROM vehiculos ORDER BY placa')
        conductores_data = fetch_all('SELECT id, nombre_completo FROM conductores ORDER BY nombre_completo')
    except Exception as e:
        flash('Error al cargar combustible.', 'error')
        logger.error("combustible GET error: %s", e)
        data, viajes_data, vehiculos_data, conductores_data = [], [], [], []
    return render_template('combustible.html', items=data, viajes=viajes_data,
                           vehiculos=vehiculos_data, conductores=conductores_data)


@app.route('/viaticos', methods=['GET', 'POST'])
@login_required
def viaticos():
    user = session['user']
    if user['rol'] not in ('Conductor', 'Supervisor', 'Administrador'):
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            import os, uuid
            comprobante_path = None
            file = request.files.get('comprobante_file')
            if file and file.filename:
                upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'viaticos')
                os.makedirs(upload_dir, exist_ok=True)
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf'):
                    flash('Tipo de archivo no permitido. Usa JPG, PNG o PDF.', 'error')
                    return redirect(url_for('viaticos'))
                fname = uuid.uuid4().hex + ext
                file.save(os.path.join(upload_dir, fname))
                comprobante_path = 'uploads/viaticos/' + fname
            execute_query(
                """INSERT INTO viaticos (viaje_id, conductor_id, tipo_gasto, valor_gasto, ciudad, fecha_gasto, comprobante, observaciones)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (request.form['viaje_id'], request.form['conductor_id'], request.form['tipo_gasto'],
                 request.form['valor_gasto'], request.form['ciudad'], request.form['fecha_gasto'],
                 comprobante_path, request.form['observaciones'])
            )
            flash('Viatico registrado correctamente.', 'success')
        except Exception as e:
            flash('Error al registrar el viatico.', 'error')
            logger.error("viaticos POST error: %s", e)
        return redirect(url_for('viaticos'))

    where, params = '', ()
    if user['rol'] == 'Conductor' and user['conductor_id']:
        where, params = 'WHERE vt.conductor_id = %s', (user['conductor_id'],)
    # Admin/Supervisor ven todos

    is_readonly = user['rol'] in ('Supervisor', 'Administrador')

    try:
        data = fetch_all(
            f"""SELECT vt.*, c.nombre_completo AS conductor, v.ciudad_origen, v.ciudad_destino
                FROM viaticos vt
                INNER JOIN conductores c ON c.id = vt.conductor_id
                INNER JOIN viajes v ON v.id = vt.viaje_id
                {where} ORDER BY vt.id DESC""",
            params
        )
        viajes_data      = fetch_all('SELECT id, ciudad_origen, ciudad_destino FROM viajes ORDER BY id DESC')
        conductores_data = fetch_all('SELECT id, nombre_completo FROM conductores ORDER BY nombre_completo')
    except Exception as e:
        flash('Error al cargar viáticos.', 'error')
        logger.error("viaticos GET error: %s", e)
        data, viajes_data, conductores_data = [], [], []
    return render_template('viaticos.html', items=data, viajes=viajes_data, conductores=conductores_data, is_readonly=is_readonly)


@app.route('/incidentes', methods=['GET', 'POST'])
@login_required
def incidentes():
    user = session['user']
    if user['rol'] not in ('Conductor',):
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            execute_query(
                """INSERT INTO incidentes (viaje_id, conductor_id, tipo_incidente, descripcion, ciudad, fecha_incidente, severidad, estado)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (request.form['viaje_id'], request.form['conductor_id'], request.form['tipo_incidente'],
                 request.form['descripcion'], request.form['ciudad'], request.form['fecha_incidente'],
                 request.form['severidad'], request.form['estado'])
            )
            flash('Incidente registrado correctamente.', 'success')
        except Exception as e:
            flash('Error al registrar el incidente.', 'error')
            logger.error("incidentes POST error: %s", e)
        return redirect(url_for('incidentes'))

    where, params = '', ()
    if user['rol'] == 'Conductor' and user['conductor_id']:
        where, params = 'WHERE i.conductor_id = %s', (user['conductor_id'],)

    try:
        data = fetch_all(
            f"""SELECT i.*, c.nombre_completo AS conductor, v.ciudad_origen, v.ciudad_destino
                FROM incidentes i
                INNER JOIN conductores c ON c.id = i.conductor_id
                INNER JOIN viajes v ON v.id = i.viaje_id
                {where} ORDER BY i.id DESC""",
            params
        )
        viajes_data      = fetch_all('SELECT id, ciudad_origen, ciudad_destino FROM viajes ORDER BY id DESC')
        conductores_data = fetch_all('SELECT id, nombre_completo FROM conductores ORDER BY nombre_completo')
    except Exception as e:
        flash('Error al cargar incidentes.', 'error')
        logger.error("incidentes GET error: %s", e)
        data, viajes_data, conductores_data = [], [], []
    return render_template('incidentes.html', items=data, viajes=viajes_data, conductores=conductores_data)


@app.route('/mantenimientos', methods=['GET', 'POST'])
@login_required
def mantenimientos():
    if session['user']['rol'] not in ('Supervisor',):
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            execute_query(
                """INSERT INTO mantenimientos (vehiculo_id, fecha_mantenimiento, tipo_mantenimiento, descripcion, kilometraje_programado, costo, estado)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (request.form['vehiculo_id'], request.form['fecha_mantenimiento'] or None,
                 request.form['tipo_mantenimiento'], request.form['descripcion'],
                 request.form['kilometraje_programado'], request.form['costo'], request.form['estado'])
            )
            flash('Mantenimiento guardado correctamente.', 'success')
        except Exception as e:
            flash('Error al guardar el mantenimiento.', 'error')
            logger.error("mantenimientos POST error: %s", e)
        return redirect(url_for('mantenimientos'))

    try:
        data           = fetch_all("SELECT m.*, v.placa FROM mantenimientos m INNER JOIN vehiculos v ON v.id = m.vehiculo_id ORDER BY m.id DESC")
        vehiculos_data = fetch_all('SELECT id, placa FROM vehiculos ORDER BY placa')
    except Exception as e:
        flash('Error al cargar mantenimientos.', 'error')
        logger.error("mantenimientos GET error: %s", e)
        data, vehiculos_data = [], []
    return render_template('mantenimientos.html', items=data, vehiculos=vehiculos_data)


@app.route('/reportes')
@login_required
def reportes():
    if session['user']['rol'] not in ('Supervisor', 'Administrador'):
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard'))
    try:
        combustible_promedio = fetch_all(
            """SELECT ve.placa, ROUND(AVG(cb.litros),2) AS promedio_litros, ROUND(SUM(cb.costo_total),2) AS costo_total
               FROM combustible cb INNER JOIN vehiculos ve ON ve.id = cb.vehiculo_id
               GROUP BY ve.placa ORDER BY costo_total DESC"""
        )
        kilometros = fetch_all(
            """SELECT ve.placa, SUM(COALESCE(v.kilometraje_fin,0) - COALESCE(v.kilometraje_inicio,0)) AS kilometros_recorridos
               FROM viajes v INNER JOIN vehiculos ve ON ve.id = v.vehiculo_id
               GROUP BY ve.placa ORDER BY kilometros_recorridos DESC"""
        )
        viaticos_data = fetch_all(
            """SELECT v.id AS viaje_id, ROUND(SUM(vt.valor_gasto),2) AS total_viaticos
               FROM viaticos vt INNER JOIN viajes v ON v.id = vt.viaje_id
               GROUP BY v.id ORDER BY total_viaticos DESC"""
        )
        incidentes_data = fetch_all(
            "SELECT tipo_incidente, COUNT(*) AS total FROM incidentes GROUP BY tipo_incidente ORDER BY total DESC"
        )
        costos_ruta = fetch_all(
            """SELECT v.ciudad_origen, v.ciudad_destino,
                      COUNT(v.id) AS total_viajes,
                      ROUND(COALESCE(SUM(cb.costo_total),0),2) AS costo_combustible,
                      ROUND(COALESCE(SUM(vt.valor_gasto),0),2) AS costo_viaticos,
                      ROUND(COALESCE(SUM(cb.costo_total),0) + COALESCE(SUM(vt.valor_gasto),0),2) AS costo_total
               FROM viajes v
               LEFT JOIN combustible cb ON cb.viaje_id = v.id
               LEFT JOIN viaticos vt ON vt.viaje_id = v.id
               GROUP BY v.ciudad_origen, v.ciudad_destino
               ORDER BY costo_total DESC"""
        )
    except Exception as e:
        flash('Error al cargar reportes.', 'error')
        logger.error("reportes error: %s", e)
        combustible_promedio, kilometros, viaticos_data, incidentes_data, costos_ruta = [], [], [], [], []
    return render_template('reportes.html', combustible_promedio=combustible_promedio,
                           kilometros=kilometros, viaticos_data=viaticos_data,
                           incidentes_data=incidentes_data, costos_ruta=costos_ruta)


@app.route('/consultas')
@login_required
def consultas():
    if session['user']['rol'] not in ('Supervisor', 'Administrador'):
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('dashboard'))
    try:
        # Todos los viajes con info completa
        viajes_raw = fetch_all(
            """SELECT v.id, v.ciudad_origen, v.ciudad_destino, v.fecha_salida, v.fecha_llegada,
                      v.estado, v.tipo_carga, v.observaciones,
                      v.kilometraje_inicio, v.kilometraje_fin,
                      v.combustible_inicio, v.combustible_fin,
                      ve.placa, ve.modelo,
                      c.id AS conductor_id, c.nombre_completo AS conductor,
                      c.telefono AS conductor_tel, c.numero_licencia, c.tipo_licencia,
                      c.ciudad AS conductor_ciudad
               FROM viajes v
               INNER JOIN vehiculos ve ON ve.id = v.vehiculo_id
               INNER JOIN conductores c ON c.id = v.conductor_id
               ORDER BY v.fecha_salida DESC"""
        )
        # Pre-formatear fechas como strings en español para el JSON del frontend
        for v in viajes_raw:
            v['fecha_salida_str']  = fecha_es(v.get('fecha_salida'),  'hora') if v.get('fecha_salida')  else '—'
            v['fecha_llegada_str'] = fecha_es(v.get('fecha_llegada'), 'hora') if v.get('fecha_llegada') else None
            # Convertir datetime a string ISO para serialización segura
            if v.get('fecha_salida')  and hasattr(v['fecha_salida'],  'isoformat'):
                v['fecha_salida']  = v['fecha_salida'].isoformat()
            if v.get('fecha_llegada') and hasattr(v['fecha_llegada'], 'isoformat'):
                v['fecha_llegada'] = v['fecha_llegada'].isoformat()

        # Conductores con stats
        conductores_raw = fetch_all(
            """SELECT c.id, c.nombre_completo, c.telefono, c.numero_licencia,
                      c.tipo_licencia, c.ciudad, c.estado, c.fecha_vencimiento_licencia,
                      COUNT(DISTINCT v.id) AS total_viajes,
                      COUNT(DISTINCT i.id) AS total_incidentes,
                      ROUND(COALESCE(SUM(DISTINCT cb.costo_total),0),0) AS gasto_combustible
               FROM conductores c
               LEFT JOIN viajes v ON v.conductor_id = c.id
               LEFT JOIN incidentes i ON i.conductor_id = c.id
               LEFT JOIN combustible cb ON cb.conductor_id = c.id
               GROUP BY c.id ORDER BY c.nombre_completo"""
        )
        for c in conductores_raw:
            if c.get('fecha_vencimiento_licencia') and hasattr(c['fecha_vencimiento_licencia'], 'isoformat'):
                c['fecha_vencimiento_licencia_str'] = fecha_es(c['fecha_vencimiento_licencia'], 'corto')
                c['fecha_vencimiento_licencia'] = c['fecha_vencimiento_licencia'].isoformat()
            else:
                c['fecha_vencimiento_licencia_str'] = c.get('fecha_vencimiento_licencia') or '—'

        viajes_data      = viajes_raw
        conductores_data = conductores_raw
    except Exception as e:
        flash('Error al cargar consultas.', 'error')
        logger.error("consultas error: %s", e)
        viajes_data, conductores_data = [], []
    return render_template('consultas.html', viajes=viajes_data, conductores=conductores_data)






# ─── Metodología Espiral ──────────────────────────────────────────────────────

@app.route('/metodologia-espiral')
@login_required
def metodologia():
    return render_template("metodologia.html")


@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html')

@app.route('/perfil/cambiar-password', methods=['POST'])
@login_required
def cambiar_password():
    from flask import jsonify
    pwd_actual  = request.form.get('pwd_actual', '').strip()
    pwd_nueva   = request.form.get('pwd_nueva', '')
    pwd_confirm = request.form.get('pwd_confirm', '')

    if not pwd_actual:
        return jsonify(ok=False, msg='Ingresa tu contrasena actual.', field='actual')
    if len(pwd_nueva) < 6:
        return jsonify(ok=False, msg='La nueva contrasena debe tener al menos 6 caracteres.', field='nueva')
    if pwd_nueva != pwd_confirm:
        return jsonify(ok=False, msg='Las contrasenias no coinciden.', field='confirm')
    if pwd_nueva == pwd_actual:
        return jsonify(ok=False, msg='La nueva contrasena debe ser diferente a la actual.', field='nueva')

    try:
        user_id = session['user']['id']
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT password FROM usuarios WHERE id = %s', (user_id,))
            row = cur.fetchone()
            if not row or not _check_password(pwd_actual, row['password']):
                conn.close()
                return jsonify(ok=False, msg='La contrasena actual es incorrecta.', field='actual')
            nuevo_hash = bcrypt.hashpw(pwd_nueva.encode(), bcrypt.gensalt()).decode()
            cur.execute('UPDATE usuarios SET password = %s WHERE id = %s', (nuevo_hash, user_id))
        conn.close()
        return jsonify(ok=True, msg='Contrasena actualizada correctamente.')
    except Exception as e:
        logger.error('Error cambiando contrasena: %s', e)
        return jsonify(ok=False, msg='Error al actualizar la contrasena. Intenta de nuevo.')

@app.route('/usuarios/toggle/<int:user_id>', methods=['POST'])
@login_required
def toggle_usuario(user_id):
    if session['user']['rol'] != 'Administrador':
        return {'ok': False, 'msg': 'Sin permisos'}, 403
    if user_id == session['user']['id']:
        return {'ok': False, 'msg': 'No puedes desactivar tu propia cuenta'}, 400
    try:
        user = fetch_one('SELECT activo FROM usuarios WHERE id = %s', (user_id,))
        if not user:
            return {'ok': False, 'msg': 'Usuario no encontrado'}, 404
        nuevo = 0 if user['activo'] else 1
        execute_query('UPDATE usuarios SET activo = %s WHERE id = %s', (nuevo, user_id))
        return {'ok': True, 'activo': nuevo}
    except Exception as e:
        logger.error('toggle_usuario error: %s', e)
        return {'ok': False, 'msg': 'Error al actualizar'}, 500


# ─── Error handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html'), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error("Error 500: %s", e)
    flash('Ocurrió un error interno. Por favor intenta de nuevo.', 'error')
    return redirect(url_for('dashboard'))


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True)