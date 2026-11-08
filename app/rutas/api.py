"""
rutas/api.py
============
Blueprint «api»: API REST de cursos que responde en formato JSON y aplica los
verbos HTTP mencionados en el video (GET, POST, PUT y DELETE).

    GET     /api/                    Documentación y consola de pruebas (HTML)
    GET     /api/cursos              Lista cursos (?q=, ?modalidad=, ?orden=, ?dir=)
    POST    /api/cursos              Crea un curso            -> 201 Created
    GET     /api/cursos/<codigo>     Obtiene un curso          -> 200 / 404
    PUT     /api/cursos/<codigo>     Reemplaza sus datos       -> 200 / 404 / 422
    DELETE  /api/cursos/<codigo>     Elimina un curso          -> 200 / 404
    GET     /api/estadisticas        Indicadores generales
"""
from flask import Blueprint, jsonify, render_template, request, url_for
from werkzeug.datastructures import MultiDict

from formularios import CursoFormulario
from modelos.curso import Curso

api_bp = Blueprint('api', __name__, url_prefix='/api')


def respuesta_error(mensaje, estado, errores=None):
    """Respuesta JSON uniforme para los errores de la API."""
    cuerpo = {'estado': estado, 'error': mensaje}
    if errores:
        cuerpo['errores'] = errores
    return jsonify(cuerpo), estado


def _leer_json():
    """Obtiene el cuerpo JSON de la petición; devuelve None si no es un objeto válido."""
    datos = request.get_json(silent=True)
    return datos if isinstance(datos, dict) else None


def _formulario_desde_json(datos):
    """Reutiliza las validaciones de CursoFormulario con los datos JSON recibidos."""
    formdata = MultiDict({clave: str(valor) for clave, valor in datos.items() if valor is not None})
    return CursoFormulario(formdata=formdata, meta={'csrf': False})


def _errores(formulario):
    """Errores de validación por campo (se descartan los errores sin campo)."""
    return {campo: mensajes for campo, mensajes in formulario.errors.items() if campo}


@api_bp.get('/')
def documentacion():
    """Página HTML que documenta la API e incluye una consola para probarla."""
    return render_template('api/documentacion.html', data={'titulo': 'API REST'})


@api_bp.get('/cursos')
def listar_cursos():
    modalidad = request.args.get('modalidad', '')
    cursos = Curso.listar(
        busqueda=request.args.get('q', '').strip(),
        modalidad=modalidad if modalidad in Curso.MODALIDADES else '',
        orden=request.args.get('orden', 'nombre'),
        direccion=request.args.get('dir', 'asc'),
    )
    return jsonify({'total': len(cursos), 'cursos': cursos})


@api_bp.get('/cursos/<codigo>')
def obtener_curso(codigo):
    curso = Curso.obtener(codigo)
    if curso is None:
        return respuesta_error(f'No existe un curso con el código {codigo.upper()}.', 404)
    return jsonify(curso)


@api_bp.post('/cursos')
def crear_curso():
    datos = _leer_json()
    if datos is None:
        return respuesta_error('Envíe un objeto JSON con la cabecera Content-Type: application/json.', 400)
    formulario = _formulario_desde_json(datos)
    if not formulario.validate():
        return respuesta_error('Los datos enviados no son válidos.', 422, _errores(formulario))
    if Curso.obtener(formulario.codigo.data):
        return respuesta_error(f'Ya existe un curso con el código {formulario.codigo.data}.', 409)

    Curso.crear(formulario.datos_curso())
    curso = Curso.obtener(formulario.codigo.data)
    respuesta = jsonify(curso)
    respuesta.status_code = 201
    respuesta.headers['Location'] = url_for('api.obtener_curso', codigo=curso['codigo'])
    return respuesta


@api_bp.put('/cursos/<codigo>')
def actualizar_curso(codigo):
    curso = Curso.obtener(codigo)
    if curso is None:
        return respuesta_error(f'No existe un curso con el código {codigo.upper()}.', 404)
    datos = _leer_json()
    if datos is None:
        return respuesta_error('Envíe un objeto JSON con la cabecera Content-Type: application/json.', 400)
    formulario = _formulario_desde_json(datos)
    del formulario.codigo  # El código de la URL identifica al curso y no se modifica.
    if not formulario.validate():
        return respuesta_error('Los datos enviados no son válidos.', 422, _errores(formulario))

    Curso.actualizar(curso['codigo'], formulario.datos_curso())
    return jsonify(Curso.obtener(curso['codigo']))


@api_bp.delete('/cursos/<codigo>')
def eliminar_curso(codigo):
    curso = Curso.obtener(codigo)
    if curso is None:
        return respuesta_error(f'No existe un curso con el código {codigo.upper()}.', 404)
    Curso.eliminar(curso['codigo'])
    return jsonify({'mensaje': f"El curso {curso['codigo']} fue eliminado correctamente."})


@api_bp.get('/estadisticas')
def estadisticas():
    return jsonify(Curso.estadisticas())
