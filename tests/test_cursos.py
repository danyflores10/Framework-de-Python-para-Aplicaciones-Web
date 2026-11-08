"""
Pruebas del CRUD web de cursos: listado, búsqueda, orden, paginación,
formularios con validación, mensajes flash y medidas de seguridad.
"""
import re


def _codigos(html):
    """Códigos de curso que aparecen en la tabla, en orden."""
    return re.findall(r'<td><span class="codigo-curso">(\w+)</span></td>', html)


def test_listado_muestra_la_tabla_de_cursos(cliente):
    respuesta = cliente.get('/gestion/cursos/')
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert '12 cursos encontrados' in html
    assert _codigos(html)[0] == 'ALG201'              # orden por nombre (A-Z)


def test_paginacion(cliente):
    pagina1 = cliente.get('/gestion/cursos/').get_data(as_text=True)
    pagina2 = cliente.get('/gestion/cursos/?pagina=2').get_data(as_text=True)
    assert 'Página 1 de 2' in pagina1 and len(_codigos(pagina1)) == 8
    assert 'Página 2 de 2' in pagina2 and len(_codigos(pagina2)) == 4


def test_pagina_fuera_de_rango_se_ajusta(cliente):
    html = cliente.get('/gestion/cursos/?pagina=99').get_data(as_text=True)
    assert 'Página 2 de 2' in html


def test_busqueda_por_query_string(cliente):
    html = cliente.get('/gestion/cursos/?q=flask').get_data(as_text=True)
    assert '1 curso encontrado para «flask»' in html
    assert _codigos(html) == ['WEB201']


def test_filtro_por_modalidad(cliente):
    html = cliente.get('/gestion/cursos/?modalidad=Virtual').get_data(as_text=True)
    assert '3 cursos encontrados' in html
    assert sorted(_codigos(html)) == ['SEG401', 'WEB202', 'WEB203']


def test_ordenamiento_por_creditos_descendente(cliente):
    html = cliente.get('/gestion/cursos/?orden=creditos&dir=desc').get_data(as_text=True)
    assert _codigos(html)[0] == 'ALG201'              # único curso de 5 créditos


def test_parametro_de_orden_no_permite_inyeccion_sql(cliente):
    respuesta = cliente.get('/gestion/cursos/?orden=nombre;DROP TABLE curso')
    assert respuesta.status_code == 200
    assert len(cliente.get('/cursos').get_json()['cursos']) == 12


def test_crear_curso_valido(cliente, curso_valido):
    respuesta = cliente.post('/gestion/cursos/nuevo', data=curso_valido, follow_redirects=True)
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert respuesta.request.path == '/gestion/cursos/IAR401'
    assert 'se registró correctamente' in html        # mensaje flash
    assert 'Inteligencia Artificial' in html


def test_crear_curso_normaliza_el_codigo(cliente, curso_valido):
    curso_valido['codigo'] = '  iar401 '
    cliente.post('/gestion/cursos/nuevo', data=curso_valido)
    assert cliente.get('/gestion/cursos/IAR401').status_code == 200


def test_crear_curso_con_codigo_duplicado(cliente, curso_valido):
    curso_valido['codigo'] = 'WEB201'
    html = cliente.post('/gestion/cursos/nuevo', data=curso_valido).get_data(as_text=True)
    assert 'Ya existe un curso registrado con ese código.' in html


def test_crear_curso_con_datos_invalidos(cliente):
    datos = {'codigo': 'WEB-1', 'nombre': 'IA', 'creditos': '20', 'docente': '', 'modalidad': 'Remota'}
    html = cliente.post('/gestion/cursos/nuevo', data=datos).get_data(as_text=True)
    assert 'Use 3 letras seguidas de 3 números' in html
    assert 'El nombre debe tener entre 3 y 80 caracteres.' in html
    assert 'Los créditos deben estar entre 1 y 10.' in html
    assert 'El nombre del docente es obligatorio.' in html
    assert 'Opción inválida.' in html                 # mensaje interno de WTForms en español
    assert 'hay campos con errores' in html


def test_creditos_deben_ser_un_numero_entero(cliente, curso_valido):
    curso_valido['creditos'] = 'cuatro'
    html = cliente.post('/gestion/cursos/nuevo', data=curso_valido).get_data(as_text=True)
    assert 'No es un valor entero válido.' in html


def test_detalle_de_un_curso(cliente):
    html = cliente.get('/gestion/cursos/WEB201').get_data(as_text=True)
    assert 'Desarrollo Web con Flask' in html
    assert 'Lucía Ramírez Soto' in html
    assert '4 créditos' in html                       # filtro personalizado «creditos»


def test_detalle_acepta_codigo_en_minusculas(cliente):
    assert cliente.get('/gestion/cursos/web201').status_code == 200


def test_detalle_de_curso_inexistente(cliente):
    assert cliente.get('/gestion/cursos/XYZ999').status_code == 404


def test_editar_curso(cliente):
    formulario = cliente.get('/gestion/cursos/WEB201/editar').get_data(as_text=True)
    assert 'value="Desarrollo Web con Flask"' in formulario   # formulario precargado
    datos = {'nombre': 'Desarrollo Web Avanzado con Flask', 'creditos': '5',
             'docente': 'Lucía Ramírez Soto', 'modalidad': 'Presencial', 'descripcion': ''}
    respuesta = cliente.post('/gestion/cursos/WEB201/editar', data=datos, follow_redirects=True)
    html = respuesta.get_data(as_text=True)
    assert 'se actualizó correctamente' in html
    assert 'Desarrollo Web Avanzado con Flask' in html
    assert '5 créditos' in html


def test_editar_no_cambia_el_codigo(cliente):
    datos = {'codigo': 'NEW999', 'nombre': 'Desarrollo Web con Flask', 'creditos': '4',
             'docente': 'Lucía Ramírez Soto', 'modalidad': 'Híbrida'}
    cliente.post('/gestion/cursos/WEB201/editar', data=datos)
    assert cliente.get('/gestion/cursos/WEB201').status_code == 200
    assert cliente.get('/gestion/cursos/NEW999').status_code == 404


def test_eliminar_curso(cliente):
    respuesta = cliente.post('/gestion/cursos/RED301/eliminar', follow_redirects=True)
    html = respuesta.get_data(as_text=True)
    assert 'fue eliminado' in html
    assert '11 cursos encontrados' in html
    assert cliente.get('/gestion/cursos/RED301').status_code == 404


def test_autoescape_de_jinja2_evita_xss(cliente, curso_valido):
    curso_valido['nombre'] = '<script>alert(1)</script>'
    cliente.post('/gestion/cursos/nuevo', data=curso_valido)
    html = cliente.get('/gestion/cursos/IAR401').get_data(as_text=True)
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html


def test_proteccion_csrf_rechaza_formularios_sin_token(tmp_path, curso_valido):
    from app import create_app
    app = create_app('pruebas', SQLITE_PATH=str(tmp_path / 'csrf.db'), WTF_CSRF_ENABLED=True)
    respuesta = app.test_client().post('/gestion/cursos/nuevo', data=curso_valido)
    assert respuesta.status_code == 400
    assert 'token de seguridad' in respuesta.get_data(as_text=True)
