"""
config.py
=========
Configuración centralizada de la aplicación «Ábaco - Gestión de Cursos».

Los valores sensibles (clave secreta y credenciales de las bases de datos) se
leen desde variables de entorno o desde el archivo ``.env`` ubicado en la raíz
del proyecto, de modo que no queden escritos dentro del código fuente.

El motor principal del proyecto es PostgreSQL (base de datos «Tarea_Flask»).
También se conserva la conexión a MySQL del video tutorial, con los mismos
nombres de parámetros (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD y MYSQL_DB).
"""
import os
from pathlib import Path

from dotenv import dotenv_values

# Rutas base del proyecto.
DIRECTORIO_APP = Path(__file__).resolve().parent      # .../gestion_cursos_flask/app
DIRECTORIO_RAIZ = DIRECTORIO_APP.parent               # .../gestion_cursos_flask
ARCHIVO_ENV = DIRECTORIO_RAIZ / '.env'

# El archivo .env se lee como un diccionario, sin copiarlo a las variables de
# entorno del sistema. Así, cuando el servidor de desarrollo se reinicia
# (por ejemplo, al guardar el .env), siempre toma los valores actuales del archivo.
_VALORES_ENV = dotenv_values(ARCHIVO_ENV) if ARCHIVO_ENV.exists() else {}


def _leer(clave, por_defecto=''):
    """Devuelve un valor de configuración.

    Prioridad: variable de entorno del sistema (si no está vacía) > archivo .env >
    valor por defecto.
    """
    valor = os.environ.get(clave) or _VALORES_ENV.get(clave)
    return por_defecto if valor is None else valor


def _motor_base_datos():
    """Lee DB_MOTOR y acepta los alias más comunes de PostgreSQL."""
    motor = _leer('DB_MOTOR', 'sqlite').strip().lower()
    return 'postgresql' if motor in ('postgres', 'postgresql', 'pg') else motor


class Config:
    """Configuración base compartida por todos los entornos."""

    # Clave con la que Flask firma la cookie de sesión y los tokens CSRF.
    SECRET_KEY = _leer('SECRET_KEY', 'clave-de-desarrollo-cambiar-en-produccion')

    # Motor de base de datos: 'postgresql' (motor principal del proyecto),
    # 'mysql' (MySQL/MariaDB, como en el video) o 'sqlite' (sin instalación).
    DB_MOTOR = _motor_base_datos()

    # Parámetros de conexión a PostgreSQL (conector psycopg).
    POSTGRES_HOST = _leer('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = int(_leer('POSTGRES_PORT', '5432'))
    POSTGRES_USER = _leer('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = _leer('POSTGRES_PASSWORD', '')
    POSTGRES_DB = _leer('POSTGRES_DB', 'Tarea_Flask')

    # Parámetros de conexión que utiliza la extensión Flask-MySQLdb (video).
    # Se usa 127.0.0.1 (equivale a «localhost» del video) porque en Windows
    # «localhost» puede intentar primero IPv6 y demorar unos 2 s cada conexión.
    MYSQL_HOST = _leer('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(_leer('MYSQL_PORT', '3306'))
    MYSQL_USER = _leer('MYSQL_USER', 'root')
    MYSQL_PASSWORD = _leer('MYSQL_PASSWORD', '')
    MYSQL_DB = _leer('MYSQL_DB', 'abaco')
    MYSQL_CHARSET = 'utf8mb4'          # Admite tildes, eñes y emojis.

    # Archivo de base de datos SQLite (se crea automáticamente si no existe).
    SQLITE_PATH = _leer('SQLITE_PATH', str(DIRECTORIO_RAIZ / 'instance' / 'abaco.db'))

    # Cantidad de cursos que se muestran por página en el listado.
    CURSOS_POR_PAGINA = int(_leer('CURSOS_POR_PAGINA', '8'))

    # Los mensajes de validación de WTForms se toman de su traducción al español.
    WTF_I18N_ENABLED = False


class DesarrolloConfig(Config):
    """Entorno de desarrollo: modo de depuración activo (recarga automática)."""

    DEBUG = True


class PruebasConfig(Config):
    """Entorno de pruebas automatizadas con pytest."""

    TESTING = True
    DB_MOTOR = 'sqlite'
    WTF_CSRF_ENABLED = False           # Facilita enviar formularios desde las pruebas.


class ProduccionConfig(Config):
    """Entorno de producción: sin depuración y con cookies más estrictas."""

    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


# Diccionario que usa la fábrica de aplicaciones para elegir la configuración.
configuraciones = {
    'desarrollo': DesarrolloConfig,
    'pruebas': PruebasConfig,
    'produccion': ProduccionConfig,
}
