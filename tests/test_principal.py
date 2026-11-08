"""
Pruebas de las rutas que reproducen el video tutorial: plantillas, Jinja2,
archivos estáticos, URLs dinámicas, query string, errores 404,
redirecciones, hooks de petición y respuesta JSON.
"""


def test_index_muestra_bienvenida_y_lista_del_video(cliente):
    respuesta = cliente.get('/')
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert '¡Saludos!' in html
    for lenguaje in ['PHP', 'Python', 'Java', 'Kotlin', 'Dart', 'JavaScript']:
        assert f'<li>{lenguaje}</li>' in html          # bucle for de Jinja2
    assert 'Total de elementos: 6' in html            # numero_cursos = len(cursos)


def test_index_muestra_estadisticas_de_la_base_de_datos(cliente):
    html = cliente.get('/').get_data(as_text=True)
    assert 'Cursos registrados' in html
    assert '<span class="dato__valor">12</span>' in html
    assert '<span class="dato__valor">44</span>' in html


def test_herencia_de_plantillas_y_archivos_estaticos(cliente):
    html = cliente.get('/').get_data(as_text=True)
    assert '<title>Inicio | Ábaco</title>' in html    # bloque title de layout.html
    assert '/static/css/layout.css' in html
    assert '/static/js/layout.js' in html
    assert cliente.get('/static/css/layout.css').status_code == 200
    assert cliente.get('/static/js/layout.js').status_code == 200


def test_url_dinamica_de_contacto(cliente):
    respuesta = cliente.get('/contacto/Oscar/28')
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert '<h1>Oscar</h1>' in html
    assert 'Tu edad es: 28' in html
    assert 'eres mayor de edad' in html


def test_url_dinamica_con_menor_de_edad(cliente):
    html = cliente.get('/contacto/Pedro/17').get_data(as_text=True)
    assert 'eres menor de edad' in html


def test_url_dinamica_exige_edad_entera(cliente):
    assert cliente.get('/contacto/Oscar/abc').status_code == 404
    assert cliente.get('/contacto/Oscar').status_code == 404


def test_formulario_de_contacto_redirige_a_la_url_dinamica(cliente):
    respuesta = cliente.post('/contacto', data={'nombre': 'Karen', 'edad': '31'})
    assert respuesta.status_code == 302
    assert respuesta.headers['Location'] == '/contacto/Karen/31'


def test_formulario_de_contacto_valida_los_datos(cliente):
    respuesta = cliente.post('/contacto', data={'nombre': 'K4ren', 'edad': '0'})
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert 'Use solo letras y espacios.' in html
    assert 'La edad debe estar entre 1 y 120 años.' in html


def test_query_string_lee_los_parametros(cliente, capsys):
    respuesta = cliente.get('/query_string?param1=Jose&param2=39')
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert '<td>Jose</td>' in html
    assert '<td>39</td>' in html
    consola = capsys.readouterr().out                 # print() como en el video
    assert 'Jose' in consola and '39' in consola


def test_query_string_sin_parametros(cliente):
    html = cliente.get('/query_string').get_data(as_text=True)
    assert 'La URL no contiene parámetros' in html


def test_pagina_404_personalizada(cliente):
    respuesta = cliente.get('/formulario')
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 404
    assert 'La página que buscas no existe' in html
    assert '<title>Página no encontrada | Ábaco</title>' in html


def test_error_404_de_la_api_responde_en_json(cliente):
    respuesta = cliente.get('/api/no-existe')
    assert respuesta.status_code == 404
    assert respuesta.is_json
    assert respuesta.get_json()['estado'] == 404


def test_redireccion_al_inicio(cliente):
    respuesta = cliente.get('/inicio')
    assert respuesta.status_code == 302
    assert respuesta.headers['Location'] == '/'


def test_hooks_before_request_y_after_request(cliente):
    respuesta = cliente.get('/')
    assert respuesta.headers['X-Tiempo-Respuesta'].endswith(' ms')
    assert respuesta.headers['X-Content-Type-Options'] == 'nosniff'
    assert respuesta.headers['X-Frame-Options'] == 'SAMEORIGIN'


def test_endpoint_json_del_video(cliente):
    respuesta = cliente.get('/cursos')
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos['mensaje'] == 'Éxito'
    assert len(datos['cursos']) == 12
    assert list(datos['cursos'][0]) == ['codigo', 'nombre', 'creditos']
    nombres = [curso['nombre'] for curso in datos['cursos']]
    assert nombres == sorted(nombres)                 # ORDER BY nombre ASC


def test_json_conserva_las_tildes(cliente):
    texto = cliente.get('/cursos').get_data(as_text=True)
    assert 'Éxito' in texto
    assert '\\u00c9' not in texto


def test_pagina_acerca_relaciona_los_capitulos_del_video(cliente):
    html = cliente.get('/acerca').get_data(as_text=True)
    assert 'Herencia de plantillas' in html
    assert 'before_request, after_request' in html
    assert 'Conexión a MySQL' in html


def test_metodo_no_permitido(cliente):
    respuesta = cliente.get('/gestion/cursos/WEB201/eliminar')
    assert respuesta.status_code == 405
    assert 'Método no permitido' in respuesta.get_data(as_text=True)
