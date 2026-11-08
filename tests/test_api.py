"""
Pruebas de la API REST (formato JSON) con los verbos GET, POST, PUT y DELETE.
"""


def test_listar_cursos(cliente):
    respuesta = cliente.get('/api/cursos')
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos['total'] == 12
    assert list(datos['cursos'][0]) == ['codigo', 'nombre', 'creditos', 'docente',
                                        'modalidad', 'descripcion', 'fecha_registro']


def test_listar_cursos_con_filtros(cliente):
    assert cliente.get('/api/cursos?q=python').get_json()['total'] == 1
    assert cliente.get('/api/cursos?modalidad=Híbrida').get_json()['total'] == 3


def test_obtener_un_curso(cliente):
    respuesta = cliente.get('/api/cursos/WEB201')
    assert respuesta.status_code == 200
    assert respuesta.get_json()['nombre'] == 'Desarrollo Web con Flask'


def test_obtener_curso_inexistente(cliente):
    respuesta = cliente.get('/api/cursos/XYZ999')
    assert respuesta.status_code == 404
    assert 'XYZ999' in respuesta.get_json()['error']


def test_crear_curso(cliente, curso_valido):
    respuesta = cliente.post('/api/cursos', json=curso_valido)
    assert respuesta.status_code == 201
    assert respuesta.headers['Location'] == '/api/cursos/IAR401'
    assert respuesta.get_json()['codigo'] == 'IAR401'
    assert cliente.get('/api/cursos').get_json()['total'] == 13


def test_crear_curso_sin_cuerpo_json(cliente):
    respuesta = cliente.post('/api/cursos', data='texto plano', content_type='text/plain')
    assert respuesta.status_code == 400


def test_crear_curso_con_errores_de_validacion(cliente):
    respuesta = cliente.post('/api/cursos', json={'codigo': '12', 'creditos': 0})
    datos = respuesta.get_json()
    assert respuesta.status_code == 422
    assert {'codigo', 'nombre', 'creditos', 'docente', 'modalidad'} <= set(datos['errores'])


def test_crear_curso_duplicado(cliente, curso_valido):
    curso_valido['codigo'] = 'WEB201'
    assert cliente.post('/api/cursos', json=curso_valido).status_code == 409


def test_actualizar_curso(cliente):
    datos = {'nombre': 'Desarrollo Web con Flask 3', 'creditos': 5,
             'docente': 'Lucía Ramírez Soto', 'modalidad': 'Virtual'}
    respuesta = cliente.put('/api/cursos/WEB201', json=datos)
    curso = respuesta.get_json()
    assert respuesta.status_code == 200
    assert curso['nombre'] == 'Desarrollo Web con Flask 3'
    assert curso['creditos'] == 5
    assert curso['descripcion'] is None               # PUT reemplaza todos los datos


def test_actualizar_curso_inexistente(cliente, curso_valido):
    assert cliente.put('/api/cursos/XYZ999', json=curso_valido).status_code == 404


def test_actualizar_curso_con_datos_invalidos(cliente):
    datos = {'nombre': 'Web', 'creditos': 99, 'docente': 'Lucía Ramírez', 'modalidad': 'Virtual'}
    respuesta = cliente.put('/api/cursos/WEB201', json=datos)
    assert respuesta.status_code == 422
    assert 'creditos' in respuesta.get_json()['errores']


def test_eliminar_curso(cliente):
    assert cliente.delete('/api/cursos/SEG401').status_code == 200
    assert cliente.get('/api/cursos/SEG401').status_code == 404
    assert cliente.delete('/api/cursos/SEG401').status_code == 404


def test_estadisticas(cliente):
    datos = cliente.get('/api/estadisticas').get_json()
    assert datos['total_cursos'] == 12
    assert datos['total_creditos'] == 44
    assert datos['promedio_creditos'] == 3.67
    assert datos['por_modalidad'][0] == {'modalidad': 'Presencial', 'cantidad': 6}


def test_pagina_de_documentacion_de_la_api(cliente):
    html = cliente.get('/api/').get_data(as_text=True)
    assert 'API REST de cursos' in html
    assert '/static/js/api.js' in html


def test_la_api_no_exige_token_csrf(tmp_path, curso_valido):
    from app import create_app
    app = create_app('pruebas', SQLITE_PATH=str(tmp_path / 'api.db'), WTF_CSRF_ENABLED=True)
    assert app.test_client().post('/api/cursos', json=curso_valido).status_code == 201
