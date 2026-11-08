"""
database.py
===========
Capa de acceso a datos de la aplicación.

Se admiten tres motores de base de datos intercambiables mediante la opción
``DB_MOTOR`` de la configuración:

* ``postgresql`` -> PostgreSQL mediante el conector psycopg y un pool de
  conexiones reutilizables. Es el motor principal del proyecto (base de datos
  «Tarea_Flask», administrada con pgAdmin).
* ``mysql``      -> MySQL o MariaDB a través de la extensión Flask-MySQLdb, tal
  como se enseña en el video tutorial (XAMPP + phpMyAdmin).
* ``sqlite``     -> SQLite, incluido en Python; permite ejecutar el proyecto sin
  instalar ningún servidor de base de datos (y se usa en las pruebas).

El resto de la aplicación no habla directamente con los conectores: usa las
funciones ``consultar`` y ``ejecutar`` de este módulo, que devuelven
diccionarios y emplean consultas parametrizadas (protección contra la
inyección SQL).
"""
import re
import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path

import click
from flask import current_app, g
from flask.cli import with_appcontext

try:
    # Conector de PostgreSQL (motor principal del proyecto).
    import psycopg
    from psycopg import sql as psql
    from psycopg.pq import TransactionStatus
except ImportError:  # pragma: no cover - depende del entorno de instalación
    psycopg = None
    psql = None
    TransactionStatus = None

try:
    # Pool de conexiones: reutiliza las conexiones a PostgreSQL entre peticiones.
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover - sin pool se abre una conexión por petición
    ConnectionPool = None

_bloqueo_pool = threading.Lock()

try:
    # Flask-MySQLdb depende del paquete mysqlclient. Si no está instalado,
    # la aplicación puede seguir funcionando con PostgreSQL o SQLite.
    import MySQLdb
    from flask_mysqldb import MySQL
except ImportError:  # pragma: no cover - depende del entorno de instalación
    MySQLdb = None
    MySQL = None

# Instancia de la extensión de MySQL. Equivale a «conexion = MySQL(app)» del
# video, pero se inicializa después con init_app() dentro de la fábrica.
conexion = MySQL() if MySQL is not None else None

# Excepciones que puede lanzar cualquiera de los tres motores.
ERRORES_BD = ((sqlite3.Error,)
              + ((psycopg.Error,) if psycopg is not None else ())
              + ((MySQLdb.Error,) if MySQLdb is not None else ()))

DIRECTORIO_SQL = Path(__file__).resolve().parent.parent / 'database'
SCRIPT_POSTGRESQL = DIRECTORIO_SQL / 'abaco_postgresql.sql'
SCRIPT_MYSQL = DIRECTORIO_SQL / 'abaco_mysql.sql'
SCRIPT_SQLITE = DIRECTORIO_SQL / 'abaco_sqlite.sql'
MOTORES_VALIDOS = ('postgresql', 'mysql', 'sqlite')
NOMBRES_MOTORES = {'postgresql': 'PostgreSQL', 'mysql': 'MySQL / MariaDB', 'sqlite': 'SQLite'}


def init_app(app):
    """Registra la base de datos elegida en la aplicación Flask."""
    motor = app.config.get('DB_MOTOR', 'sqlite')
    if motor not in MOTORES_VALIDOS:
        raise ValueError(f"DB_MOTOR debe ser 'postgresql', 'mysql' o 'sqlite' (se recibió '{motor}').")

    if motor == 'mysql':
        if conexion is None:
            raise RuntimeError('Para usar MySQL instale: pip install flask-mysqldb mysqlclient')
        conexion.init_app(app)
    elif motor == 'postgresql':
        if psycopg is None:
            raise RuntimeError('Para usar PostgreSQL instale: pip install "psycopg[binary]"')
        app.teardown_appcontext(cerrar_conexion)
        _preparar_postgresql(app)
    else:
        app.teardown_appcontext(cerrar_conexion)
        # Primera ejecución: crea el archivo .db con la tabla y los datos de ejemplo.
        if not Path(app.config['SQLITE_PATH']).exists():
            with app.app_context():
                inicializar_bd()

    app.cli.add_command(comando_init_db)


def _parametros_postgresql(configuracion, base=None):
    """Parámetros de conexión de psycopg tomados de la configuración (.env)."""
    return {
        'host': configuracion['POSTGRES_HOST'],
        'port': configuracion['POSTGRES_PORT'],
        'user': configuracion['POSTGRES_USER'],
        'password': configuracion['POSTGRES_PASSWORD'] or None,
        'dbname': base or configuracion['POSTGRES_DB'],
        'connect_timeout': 5,
        'client_encoding': 'UTF8',
    }


def explicar_error_postgresql(error):
    """Traduce los errores de conexión más comunes a una indicación clara."""
    texto = str(error).lower()
    if 'password' in texto or 'contrase' in texto:
        return ('La contraseña no es correcta o está vacía: escriba en POSTGRES_PASSWORD (archivo .env) '
                'la contraseña del usuario postgres que definió al instalar PostgreSQL.')
    if 'does not exist' in texto or 'no existe' in texto:
        return 'La base de datos indicada en POSTGRES_DB no existe: créela en pgAdmin o revise su nombre.'
    if 'refused' in texto or 'rechaz' in texto or 'timeout' in texto or 'could not connect' in texto:
        return ('No se pudo llegar al servidor: verifique que el servicio de PostgreSQL esté iniciado '
                'y que POSTGRES_HOST y POSTGRES_PORT sean correctos (por defecto localhost y 5432).')
    return 'Revise los valores POSTGRES_* del archivo .env.'


def _preparar_postgresql(app):
    """Crea la base de datos y la tabla «curso» si todavía no existen."""
    try:
        _crear_base_postgresql_si_falta(app.config)
        with psycopg.connect(**_parametros_postgresql(app.config)) as bd:
            existe = bd.execute("SELECT to_regclass('public.curso') IS NOT NULL").fetchone()[0]
        if not existe:
            with app.app_context():
                inicializar_bd()
            app.logger.info('Se creó la tabla «curso» con 12 cursos de ejemplo en PostgreSQL (%s).',
                            app.config['POSTGRES_DB'])
    except psycopg.Error as error:
        app.logger.warning('No se pudo conectar con PostgreSQL. %s', explicar_error_postgresql(error))


def _pool_postgresql():
    """Devuelve el pool de conexiones de PostgreSQL de la aplicación (lo crea la primera vez).

    Reutilizar conexiones evita abrir una nueva en cada petición: en Windows,
    PostgreSQL crea un proceso y autentica al usuario por cada conexión.
    """
    app = current_app._get_current_object()
    pool = app.extensions.get('pool_postgresql')
    if pool is not None:
        return pool
    with _bloqueo_pool:
        pool = app.extensions.get('pool_postgresql')
        if pool is None:
            parametros = _parametros_postgresql(app.config)
            psycopg.connect(**parametros).close()  # Si no hay acceso, falla rápido con el error real.
            pool = ConnectionPool(kwargs=parametros, min_size=1, max_size=10, timeout=10,
                                  open=False, name='tarea_flask')
            try:
                pool.open(wait=True, timeout=10)
            except Exception:
                pool.close()
                raise
            app.extensions['pool_postgresql'] = pool
    return pool


def cerrar_pool(app):
    """Cierra el pool de conexiones de PostgreSQL (por ejemplo, al terminar las pruebas)."""
    pool = app.extensions.pop('pool_postgresql', None)
    if pool is not None:
        pool.close()


def _crear_base_postgresql_si_falta(configuracion):
    """Crea la base indicada en POSTGRES_DB si no existe (requiere la base «postgres»)."""
    nombre_bd = configuracion['POSTGRES_DB'] or ''
    if not re.fullmatch(r'[A-Za-z0-9_]+', nombre_bd):
        raise ValueError('POSTGRES_DB solo puede contener letras, números y guion bajo.')
    try:
        with psycopg.connect(**_parametros_postgresql(configuracion, base='postgres'),
                             autocommit=True) as administrador:
            existe = administrador.execute('SELECT 1 FROM pg_database WHERE datname = %s',
                                           (nombre_bd,)).fetchone()
            if existe is None:
                administrador.execute(psql.SQL('CREATE DATABASE {}').format(psql.Identifier(nombre_bd)))
    except psycopg.OperationalError:
        # Sin acceso a la base «postgres»: se asume que la base ya fue creada
        # (por ejemplo, en pgAdmin). Si hay otro problema, aparecerá al conectar.
        pass


def obtener_conexion():
    """Devuelve la conexión de la petición actual (una por contexto de aplicación)."""
    motor = current_app.config['DB_MOTOR']
    if motor == 'mysql':
        return conexion.connection
    if 'conexion_bd' not in g:
        if motor == 'postgresql' and ConnectionPool is not None:
            pool = _pool_postgresql()
            g.conexion_bd = pool.getconn()   # Toma una conexión libre del pool.
            g.pool_bd = pool
        elif motor == 'postgresql':
            g.conexion_bd = psycopg.connect(**_parametros_postgresql(current_app.config))
        else:
            ruta = Path(current_app.config['SQLITE_PATH'])
            ruta.parent.mkdir(parents=True, exist_ok=True)
            g.conexion_bd = sqlite3.connect(ruta)
    return g.conexion_bd


def cerrar_conexion(_excepcion=None):
    """Al terminar la petición devuelve la conexión al pool (PostgreSQL) o la cierra (SQLite)."""
    bd = g.pop('conexion_bd', None)
    pool = g.pop('pool_bd', None)
    if bd is None:
        return
    if pool is None:
        bd.close()
        return
    try:
        if bd.info.transaction_status != TransactionStatus.IDLE:
            bd.rollback()  # Cierra la transacción de lectura antes de devolver la conexión.
    except psycopg.Error:
        pass  # El pool descarta automáticamente las conexiones dañadas.
    finally:
        pool.putconn(bd)


def operador_busqueda():
    """Operador para búsquedas de texto sin distinguir mayúsculas y minúsculas.

    En PostgreSQL, LIKE distingue mayúsculas; ILIKE no lo hace. En MySQL y en
    SQLite, LIKE ya ignora las mayúsculas.
    """
    return 'ILIKE' if current_app.config['DB_MOTOR'] == 'postgresql' else 'LIKE'


def _adaptar(sql):
    """Adapta los marcadores de parámetros: PostgreSQL y MySQL usan %s; SQLite usa ?."""
    if current_app.config['DB_MOTOR'] == 'sqlite':
        return sql.replace('%s', '?')
    return sql


def _normalizar(valor):
    """Convierte fechas a texto para que los tres motores devuelvan lo mismo."""
    if isinstance(valor, datetime):
        return valor.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(valor, date):
        return valor.isoformat()
    return valor


def consultar(sql, parametros=(), uno=False):
    """Ejecuta una consulta SELECT y devuelve una lista de diccionarios.

    Si ``uno`` es True devuelve solo el primer registro (o None).
    """
    conexion_bd = obtener_conexion()
    cursor = conexion_bd.cursor()
    try:
        cursor.execute(_adaptar(sql), tuple(parametros))
        columnas = [columna[0] for columna in cursor.description]
        filas = cursor.fetchall()
    finally:
        cursor.close()
    registros = [{col: _normalizar(val) for col, val in zip(columnas, fila)} for fila in filas]
    if uno:
        return registros[0] if registros else None
    return registros


def ejecutar(sql, parametros=()):
    """Ejecuta INSERT, UPDATE o DELETE, confirma la transacción y devuelve
    la cantidad de filas afectadas. Si ocurre un error, revierte los cambios."""
    conexion_bd = obtener_conexion()
    cursor = conexion_bd.cursor()
    try:
        cursor.execute(_adaptar(sql), tuple(parametros))
        conexion_bd.commit()
        return cursor.rowcount
    except Exception:
        conexion_bd.rollback()
        raise
    finally:
        cursor.close()


def _dividir_sentencias(script):
    """Separa un script SQL en sentencias individuales e ignora los comentarios."""
    lineas = [linea for linea in script.splitlines() if not linea.strip().startswith('--')]
    return [sentencia.strip() for sentencia in '\n'.join(lineas).split(';') if sentencia.strip()]


def inicializar_bd():
    """Crea (o vuelve a crear) la tabla «curso» con los datos de ejemplo."""
    motor = current_app.config['DB_MOTOR']
    if motor == 'postgresql':
        _inicializar_postgresql()
    elif motor == 'mysql':
        _inicializar_mysql()
    else:
        _inicializar_sqlite()


def _inicializar_postgresql():
    configuracion = current_app.config
    _crear_base_postgresql_si_falta(configuracion)
    sentencias = _dividir_sentencias(SCRIPT_POSTGRESQL.read_text(encoding='utf-8'))
    # El bloque «with» confirma la transacción al terminar y cierra la conexión.
    with psycopg.connect(**_parametros_postgresql(configuracion)) as bd:
        with bd.cursor() as cursor:
            for sentencia in sentencias:
                cursor.execute(sentencia)


def _inicializar_sqlite():
    ruta = Path(current_app.config['SQLITE_PATH'])
    ruta.parent.mkdir(parents=True, exist_ok=True)
    bd = sqlite3.connect(ruta)
    try:
        bd.executescript(SCRIPT_SQLITE.read_text(encoding='utf-8'))
        bd.commit()
    finally:
        bd.close()


def _inicializar_mysql():
    configuracion = current_app.config
    nombre_bd = configuracion['MYSQL_DB'] or ''
    if not re.fullmatch(r'[A-Za-z0-9_]+', nombre_bd):
        raise ValueError('MYSQL_DB solo puede contener letras, números y guion bajo.')

    parametros = {
        'host': configuracion['MYSQL_HOST'],
        'port': configuracion['MYSQL_PORT'],
        'user': configuracion['MYSQL_USER'],
        'charset': 'utf8mb4',
    }
    if configuracion['MYSQL_PASSWORD']:
        parametros['passwd'] = configuracion['MYSQL_PASSWORD']

    # El script trae «CREATE DATABASE abaco» y «USE abaco» para phpMyAdmin;
    # aquí se reemplazan por el nombre configurado en MYSQL_DB.
    sentencias = [
        sentencia for sentencia in _dividir_sentencias(SCRIPT_MYSQL.read_text(encoding='utf-8'))
        if not sentencia.upper().startswith(('CREATE DATABASE', 'USE '))
    ]
    bd = MySQLdb.connect(**parametros)
    try:
        cursor = bd.cursor()
        cursor.execute(
            f'CREATE DATABASE IF NOT EXISTS `{nombre_bd}` '
            'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
        )
        cursor.execute(f'USE `{nombre_bd}`')
        for sentencia in sentencias:
            cursor.execute(sentencia)
        bd.commit()
        cursor.close()
    finally:
        bd.close()


@click.command('init-db')
@with_appcontext
def comando_init_db():
    """Crea la tabla «curso» e inserta los 12 cursos de ejemplo."""
    inicializar_bd()
    configuracion = current_app.config
    motor = configuracion['DB_MOTOR']
    destino = {
        'postgresql': configuracion['POSTGRES_DB'],
        'mysql': configuracion['MYSQL_DB'],
        'sqlite': configuracion['SQLITE_PATH'],
    }[motor]
    click.echo(f'Base de datos inicializada correctamente ({NOMBRES_MOTORES[motor]}: {destino}).')
