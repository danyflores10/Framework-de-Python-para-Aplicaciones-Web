"""
app.py
======
Punto de entrada de «Ábaco - Gestión de Cursos», aplicación web construida con
el microframework Flask a partir del video «Tutorial Flask: Framework de Python
para Aplicaciones Web (Desde Cero)» del canal UskoKruM2010.

Ejecución (igual que en el video, desde la carpeta raíz del proyecto):
    python app/app.py

Ejecución con la interfaz de línea de comandos de Flask:
    flask --app app/app.py run --debug
"""
import logging
import time
from datetime import datetime
from importlib.metadata import version

from flask import Flask, g, jsonify, render_template, request
from flask_wtf.csrf import CSRFError, CSRFProtect

import database
from config import ARCHIVO_ENV, configuraciones
from rutas.api import api_bp
from rutas.cursos import cursos_bp
from rutas.principal import principal_bp

# Extensión de seguridad: valida un token CSRF en todos los formularios POST.
csrf = CSRFProtect()


def create_app(nombre_configuracion='desarrollo', **ajustes):
    """Fábrica de aplicaciones: crea, configura y devuelve una instancia de Flask.

    Se nombra en inglés porque el comando «flask --app app/app.py run» busca
    automáticamente una función llamada create_app.

    :param nombre_configuracion: 'desarrollo', 'pruebas' o 'produccion'.
    :param ajustes: valores que sobrescriben la configuración (útil en pruebas).
    """
    app = Flask(__name__)  # Igual que en el video: app = Flask(__name__)
    app.config.from_object(configuraciones[nombre_configuracion])
    app.config.update(ajustes)

    # Respuestas JSON con tildes legibles y con el mismo orden de las columnas.
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    app.logger.setLevel(logging.INFO)

    database.init_app(app)       # PostgreSQL (psycopg), MySQL (Flask-MySQLdb) o SQLite.
    csrf.init_app(app)           # Protección CSRF para los formularios HTML.

    # Blueprints: módulos de rutas independientes.
    app.register_blueprint(principal_bp)
    app.register_blueprint(cursos_bp)
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)          # La API recibe JSON, no formularios HTML.

    registrar_hooks(app)
    registrar_manejadores_de_error(app)
    registrar_utilidades_de_plantilla(app)

    if not app.debug and not app.testing and 'cambiar' in app.config['SECRET_KEY']:
        app.logger.warning('Defina una SECRET_KEY propia en el archivo .env antes de publicar la aplicación.')
    return app


def registrar_hooks(app):
    """Funciones que se ejecutan antes y después de cada petición (video: minuto 39:13)."""

    @app.before_request
    def before_request():
        g.inicio_peticion = time.perf_counter()
        if not request.path.startswith('/static/'):
            app.logger.info('Antes de la petición: %s %s', request.method, request.full_path.rstrip('?'))

    @app.after_request
    def after_request(response):
        inicio = g.get('inicio_peticion')
        duracion_ms = (time.perf_counter() - inicio) * 1000 if inicio else 0.0
        response.headers['X-Tiempo-Respuesta'] = f'{duracion_ms:.2f} ms'
        # Cabeceras de seguridad recomendadas para cualquier aplicación web.
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        if not request.path.startswith('/static/'):
            app.logger.info('Después de la petición: %s %s -> %s (%.2f ms)', request.method,
                            request.path, response.status_code, duracion_ms)
        return response  # after_request siempre debe devolver la respuesta.


def _respuesta_error(codigo, titulo, mensaje):
    """Devuelve el error en JSON para la API o en HTML para el navegador."""
    if request.path.startswith('/api/'):
        return jsonify({'estado': codigo, 'error': mensaje}), codigo
    return render_template('error.html', codigo=codigo, titulo=titulo, mensaje=mensaje), codigo


def registrar_manejadores_de_error(app):
    """Páginas de error personalizadas (video: «404 Not Found» y «Redirecciones»)."""

    def pagina_no_encontrada(error):
        if request.path.startswith('/api/'):
            return jsonify({'estado': 404, 'error': 'Recurso no encontrado.'}), 404
        return render_template('404.html'), 404
        # Alternativa mostrada en el video: redirigir al inicio en lugar de
        # mostrar la plantilla (requiere importar redirect y url_for).
        # return redirect(url_for('principal.index'))

    def metodo_no_permitido(error):
        return _respuesta_error(405, 'Método no permitido',
                                f'La ruta {request.path} no acepta peticiones {request.method}.')

    def error_csrf(error):
        return _respuesta_error(400, 'Formulario no válido',
                                'El token de seguridad del formulario no es válido o expiró. '
                                'Vuelva a cargar la página e inténtelo de nuevo.')

    def error_base_datos(error):
        app.logger.error('Error de base de datos: %s', error)
        if app.config['DB_MOTOR'] == 'postgresql':
            mensaje = ('No fue posible comunicarse con PostgreSQL. '
                       f'{database.explicar_error_postgresql(error)} '
                       'Al guardar el archivo .env, el servidor de desarrollo se reinicia solo; '
                       'luego recargue esta página.')
        else:
            mensaje = ('No fue posible comunicarse con la base de datos. Si usa MySQL, inicie el '
                       'servicio en XAMPP y revise las credenciales MYSQL_* del archivo .env.')
        return _respuesta_error(503, 'Base de datos no disponible', mensaje)

    def error_interno(error):
        return _respuesta_error(500, 'Error interno del servidor',
                                'Ocurrió un error inesperado. Inténtelo nuevamente más tarde.')

    # Registro de manejadores con register_error_handler, igual que en el video.
    app.register_error_handler(404, pagina_no_encontrada)
    app.register_error_handler(405, metodo_no_permitido)
    app.register_error_handler(CSRFError, error_csrf)
    for tipo_error in database.ERRORES_BD:
        app.register_error_handler(tipo_error, error_base_datos)
    app.register_error_handler(500, error_interno)


def registrar_utilidades_de_plantilla(app):
    """Variables globales y filtros personalizados para las plantillas Jinja2."""
    version_flask = version('flask')

    @app.context_processor
    def variables_globales():
        return {
            'nombre_app': 'Ábaco',
            'anio_actual': datetime.now().year,
            'motor_bd': app.config['DB_MOTOR'],
            'nombre_motor_bd': database.NOMBRES_MOTORES[app.config['DB_MOTOR']],
            'version_flask': version_flask,
        }

    @app.template_filter('creditos')
    def filtro_creditos(valor):
        """{{ 4|creditos }} -> '4 créditos'."""
        return f'{valor} crédito' if valor == 1 else f'{valor} créditos'

    @app.template_filter('fecha')
    def filtro_fecha(valor):
        """{{ '2026-11-06 10:30:00'|fecha }} -> '06/11/2026 10:30'."""
        try:
            return datetime.strptime(str(valor)[:19], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
        except ValueError:
            return valor


if __name__ == '__main__':
    app = create_app()
    # Igual que en el video: app.run(debug=True, port=5000). Además, el servidor
    # vigila el archivo .env y se reinicia solo cuando se guarda (por ejemplo, al
    # escribir la contraseña de PostgreSQL); load_dotenv=False evita que Flask
    # copie el .env a las variables del sistema y se queden valores antiguos.
    app.run(debug=True, port=5000, load_dotenv=False, extra_files=[str(ARCHIVO_ENV)])
