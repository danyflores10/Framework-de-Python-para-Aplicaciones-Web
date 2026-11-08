"""
rutas/cursos.py
===============
Blueprint «cursos»: gestión web completa de cursos (CRUD) con plantillas
Jinja2, formularios Flask-WTF, mensajes flash, búsqueda mediante query
string, ordenamiento por columnas y paginación.

Es la ampliación natural del video: allí los cursos se devolvían en JSON y
se sugería mostrarlos en una tabla HTML; aquí además se pueden registrar,
editar y eliminar.

    GET        /gestion/cursos/                 Listado (tabla HTML)
    GET, POST  /gestion/cursos/nuevo            Registrar un curso
    GET        /gestion/cursos/<codigo>         Ver detalle
    GET, POST  /gestion/cursos/<codigo>/editar  Editar un curso
    POST       /gestion/cursos/<codigo>/eliminar Eliminar un curso
"""
import math

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from formularios import CursoFormulario
from modelos.curso import Curso

cursos_bp = Blueprint('cursos', __name__, url_prefix='/gestion/cursos')


def _filtros_desde_query_string():
    """Lee y valida los filtros enviados en la URL (?q=...&modalidad=...&orden=...&dir=...)."""
    busqueda = request.args.get('q', '').strip()[:60]
    modalidad = request.args.get('modalidad', '')
    orden = request.args.get('orden', 'nombre')
    return {
        'q': busqueda,
        'modalidad': modalidad if modalidad in Curso.MODALIDADES else '',
        'orden': orden if orden in Curso.COLUMNAS_ORDEN else 'nombre',
        'dir': 'desc' if request.args.get('dir') == 'desc' else 'asc',
    }


def _obtener_o_404(codigo):
    """Devuelve el curso solicitado o responde con el error 404."""
    curso = Curso.obtener(codigo)
    if curso is None:
        abort(404)
    return curso


@cursos_bp.route('/')
def listar():
    """Tabla de cursos con búsqueda, filtro por modalidad, orden y paginación."""
    filtros = _filtros_desde_query_string()
    por_pagina = current_app.config['CURSOS_POR_PAGINA']
    total = Curso.contar(filtros['q'], filtros['modalidad'])
    total_paginas = max(1, math.ceil(total / por_pagina))
    pagina = min(max(request.args.get('pagina', 1, type=int), 1), total_paginas)

    cursos = Curso.listar(filtros['q'], filtros['modalidad'], filtros['orden'], filtros['dir'],
                          limite=por_pagina, desplazamiento=(pagina - 1) * por_pagina)

    def url_listado(**cambios):
        """Construye la URL del listado conservando los filtros actuales.
        Omite los valores por defecto para que la URL quede corta y legible."""
        parametros = {**filtros, 'pagina': pagina, **cambios}
        por_defecto = {'q': '', 'modalidad': '', 'orden': 'nombre', 'dir': 'asc', 'pagina': 1}
        return url_for('cursos.listar', **{clave: valor for clave, valor in parametros.items()
                                           if valor != por_defecto.get(clave)})

    return render_template('cursos/listar.html', cursos=cursos, filtros=filtros, total=total,
                           pagina=pagina, total_paginas=total_paginas, url_listado=url_listado,
                           modalidades=Curso.MODALIDADES, data={'titulo': 'Cursos'})


@cursos_bp.route('/nuevo', methods=['GET', 'POST'])
def crear():
    """Registra un curso nuevo (GET muestra el formulario, POST lo procesa)."""
    formulario = CursoFormulario()
    if formulario.validate_on_submit():
        if Curso.obtener(formulario.codigo.data):
            formulario.codigo.errors.append('Ya existe un curso registrado con ese código.')
        else:
            Curso.crear(formulario.datos_curso())
            flash(f'El curso «{formulario.nombre.data}» se registró correctamente.', 'exito')
            return redirect(url_for('cursos.detalle', codigo=formulario.codigo.data))
    if request.method == 'POST':
        flash('Revise los datos del formulario: hay campos con errores.', 'error')
    return render_template('cursos/formulario.html', formulario=formulario, modo='crear',
                           data={'titulo': 'Registrar curso'})


@cursos_bp.route('/<codigo>')
def detalle(codigo):
    """Muestra toda la información de un curso."""
    curso = _obtener_o_404(codigo)
    return render_template('cursos/detalle.html', curso=curso, data={'titulo': curso['nombre']})


@cursos_bp.route('/<codigo>/editar', methods=['GET', 'POST'])
def editar(codigo):
    """Edita un curso existente. El formulario se precarga con los datos actuales."""
    curso = _obtener_o_404(codigo)
    formulario = CursoFormulario(data=curso)
    del formulario.codigo  # El código es la clave primaria: no se modifica.
    if formulario.validate_on_submit():
        Curso.actualizar(curso['codigo'], formulario.datos_curso())
        flash(f'El curso «{formulario.nombre.data}» se actualizó correctamente.', 'exito')
        return redirect(url_for('cursos.detalle', codigo=curso['codigo']))
    if request.method == 'POST':
        flash('Revise los datos del formulario: hay campos con errores.', 'error')
    return render_template('cursos/formulario.html', formulario=formulario, modo='editar',
                           curso=curso, data={'titulo': f"Editar {curso['codigo']}"})


@cursos_bp.route('/<codigo>/eliminar', methods=['POST'])
def eliminar(codigo):
    """Elimina un curso. Solo acepta POST (con token CSRF) para evitar borrados por enlace."""
    curso = _obtener_o_404(codigo)
    Curso.eliminar(curso['codigo'])
    flash(f"El curso «{curso['nombre']}» ({curso['codigo']}) fue eliminado.", 'exito')
    return redirect(url_for('cursos.listar'))
