"""
rutas/principal.py
==================
Blueprint «principal»: reúne las rutas que reproducen, paso a paso, lo que se
enseña en el video tutorial de Flask:

* ``/``                               Vista index con plantilla y datos dinámicos.
* ``/contacto/<nombre>/<int:edad>``   URL dinámica con parámetros.
* ``/query_string``                   Lectura de parámetros con request.args
                                      (registrada con add_url_rule).
* ``/inicio``                         Ejemplo de redirección con redirect y url_for.
* ``/cursos``                         Listado de cursos en formato JSON desde la base
                                      de datos (PostgreSQL, MySQL o SQLite).

Además incluye el formulario de contacto y la página «Acerca del proyecto».
"""
import platform
from importlib.metadata import PackageNotFoundError, version

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from database import ERRORES_BD
from formularios import ContactoFormulario
from modelos.curso import Curso

principal_bp = Blueprint('principal', __name__)


@principal_bp.route('/')
def index():
    """Página de inicio (video: «Rutas y vistas», «Plantillas» y «Jinja2»)."""
    # Primera versión del video: devolver texto o HTML directamente.
    # return "<h1>UskoKruM2010 - Suscríbete!</h1>"
    cursos = ['PHP', 'Python', 'Java', 'Kotlin', 'Dart', 'JavaScript']
    data = {
        'titulo': 'Inicio',
        'bienvenida': '¡Saludos!',
        'cursos': cursos,
        'numero_cursos': len(cursos),
    }
    # Indicadores obtenidos desde la base de datos. Si la base no está
    # disponible, la página igual se muestra con un aviso.
    try:
        data['estadisticas'] = Curso.estadisticas()
        data['recientes'] = Curso.listar(orden='fecha_registro', direccion='desc', limite=4)
    except ERRORES_BD as error:
        current_app.logger.warning('Base de datos no disponible: %s', error)
        data['estadisticas'] = None
        data['recientes'] = []
    return render_template('index.html', data=data)


@principal_bp.route('/inicio')
def inicio():
    """Redirección (video: «Redirecciones»): /inicio lleva a la ruta raíz."""
    return redirect(url_for('principal.index'))


@principal_bp.route('/contacto', methods=['GET', 'POST'])
def contacto_formulario():
    """Formulario que construye la URL dinámica de contacto (GET muestra, POST procesa)."""
    formulario = ContactoFormulario()
    if formulario.validate_on_submit():
        # Patrón Post/Redirect/Get: tras un POST válido se redirige a otra URL.
        return redirect(url_for('principal.contacto',
                                nombre=formulario.nombre.data,
                                edad=formulario.edad.data))
    return render_template('contacto_formulario.html', formulario=formulario,
                           data={'titulo': 'Contacto'})


@principal_bp.route('/contacto/<nombre>/<int:edad>')
def contacto(nombre, edad):
    """URL dinámica (video: «URLs dinámicas»). El convertidor int exige un entero."""
    data = {
        'titulo': 'Contacto',
        'nombre': nombre,
        'edad': edad,
    }
    return render_template('contacto.html', data=data)


def query_string():
    """Query string (video: minuto 29:53). Ejemplo: /query_string?param1=Jose&param2=39"""
    # Igual que en el video, se imprimen los datos en la consola del servidor.
    print(request)
    print(request.args)
    print(request.args.get('param1'))
    print(request.args.get('param2'))
    data = {
        'titulo': 'Query String',
        'metodo': request.method,
        'ruta': request.path,
        'url_completa': request.full_path.rstrip('?'),
        'parametros': list(request.args.items(multi=True)),
        'param1': request.args.get('param1'),
        'param2': request.args.get('param2'),
    }
    return render_template('query_string.html', data=data)


# Registro de una ruta SIN decorador, mediante add_url_rule (como en el video).
principal_bp.add_url_rule('/query_string', view_func=query_string)


@principal_bp.route('/cursos')
def listar_cursos():
    """Listado de cursos en JSON (video: «Conexión a MySQL» y «Respuesta JSON»)."""
    data = {}
    try:
        cursos = Curso.listar_basico()  # SELECT codigo, nombre, creditos FROM curso ORDER BY nombre ASC
        data['cursos'] = cursos
        data['mensaje'] = 'Éxito'
    except Exception as ex:  # noqa: BLE001 - se informa cualquier fallo de conexión o consulta
        current_app.logger.error('Error al listar cursos: %s', ex)
        data['mensaje'] = 'Error'
        return jsonify(data), 503
    return jsonify(data)


@principal_bp.route('/acerca')
def acerca():
    """Relación entre los capítulos del video y las funciones del proyecto."""
    capitulos = [
        ('0:00', 'Introducción', 'Objetivo: crear una aplicación web con Flask y MySQL.', None),
        ('1:13', 'Creación de entorno virtual', 'Entorno «env» creado con venv o virtualenv (README.md).', None),
        ('2:32', 'Instalación de Flask', 'Dependencias con versiones fijas en requirements.txt.', None),
        ('3:27', 'Primera aplicación web', 'app/app.py: Flask(__name__) y app.run().', url_for('principal.index')),
        ('5:30', 'Rutas y vistas', 'Decorador @route en los blueprints de la carpeta rutas.', url_for('principal.index')),
        ('7:45', 'Modo de depuración', 'app.run(debug=True, port=5000) con recarga automática.', None),
        ('9:11', 'Respuesta HTML', 'Las vistas devuelven documentos HTML completos.', url_for('principal.index')),
        ('10:28', 'Plantillas (Templates)', 'Carpeta app/templates y función render_template().', url_for('principal.index')),
        ('12:19', 'Contenido HTML dinámico', 'Diccionario «data» enviado a las plantillas.', url_for('principal.index')),
        ('13:24', 'Motor de plantillas Jinja2', 'Interpolación {{ }}, filtros personalizados y macros.', url_for('cursos.listar')),
        ('15:32', 'Iteración de listas', 'Bucles for y condicionales if/else en las plantillas.', url_for('principal.index')),
        ('18:15', 'Herencia de plantillas', 'layout.html con los bloques title, body y scripts.', url_for('principal.index')),
        ('22:04', 'Archivos estáticos', 'static/css/layout.css y static/js/layout.js con url_for().',
         url_for('static', filename='css/layout.css')),
        ('25:40', 'URLs dinámicas (parámetros)', 'Ruta /contacto/<nombre>/<int:edad>.',
         url_for('principal.contacto', nombre='Oscar', edad=28)),
        ('29:53', 'Query String', 'request.args en /query_string, registrada con add_url_rule().',
         url_for('principal.query_string', param1='Jose', param2=39)),
        ('34:35', '404 Not Found', 'register_error_handler(404) con la plantilla 404.html.', '/formulario'),
        ('37:50', 'Redirecciones', 'redirect(url_for(...)) en /inicio y después de guardar.', url_for('principal.inicio')),
        ('39:13', 'before_request, after_request', 'Registro de peticiones y cabecera X-Tiempo-Respuesta.', None),
        ('40:54', 'Conexión a MySQL', 'Flask-MySQLdb como en el video; el proyecto usa PostgreSQL (Tarea_Flask).',
         url_for('cursos.listar')),
        ('44:41', 'Respuesta JSON', 'jsonify() en /cursos y en la API REST /api/cursos.', url_for('principal.listar_cursos')),
        ('47:31', 'Despedida', 'Mejoras sugeridas: tabla HTML, estilos y CRUD completo.', url_for('cursos.listar')),
    ]
    paquetes = ['Flask', 'Werkzeug', 'Jinja2', 'itsdangerous', 'click', 'blinker', 'MarkupSafe',
                'Flask-WTF', 'WTForms', 'psycopg', 'Flask-MySQLdb', 'mysqlclient', 'python-dotenv']
    versiones = [('Python', platform.python_version())]
    for paquete in paquetes:
        try:
            versiones.append((paquete, version(paquete)))
        except PackageNotFoundError:
            versiones.append((paquete, 'no instalado'))
    return render_template('acerca.html', capitulos=capitulos, versiones=versiones,
                           data={'titulo': 'Acerca del proyecto'})
