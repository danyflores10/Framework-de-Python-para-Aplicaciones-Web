"""
Pruebas de integración con MySQL / MariaDB (opcionales).

Solo se ejecutan si se define la variable de entorno PRUEBAS_MYSQL=1 y hay un
servidor disponible con las credenciales MYSQL_* del archivo .env. Utilizan
una base de datos aparte (por defecto «abaco_pruebas») que se elimina al
terminar, por lo que nunca modifican la base «abaco» real.

    PowerShell:   $env:PRUEBAS_MYSQL="1"; python -m pytest -m mysql -v
    Linux/macOS:  PRUEBAS_MYSQL=1 python -m pytest -m mysql -v
"""
import os

import pytest

pytestmark = [
    pytest.mark.mysql,
    pytest.mark.skipif(os.getenv('PRUEBAS_MYSQL') != '1',
                       reason='Defina PRUEBAS_MYSQL=1 para ejecutar las pruebas con MySQL.'),
]

BD_PRUEBAS = os.getenv('MYSQL_DB_PRUEBAS', 'abaco_pruebas')


@pytest.fixture()
def app_mysql():
    import MySQLdb

    import database
    from app import create_app

    aplicacion = create_app('pruebas', DB_MOTOR='mysql', MYSQL_DB=BD_PRUEBAS)
    if BD_PRUEBAS == os.getenv('MYSQL_DB', 'abaco'):
        pytest.skip('La base de pruebas no puede ser la misma que la base real.')
    with aplicacion.app_context():
        database.inicializar_bd()

    yield aplicacion

    configuracion = aplicacion.config
    parametros = {'host': configuracion['MYSQL_HOST'], 'port': configuracion['MYSQL_PORT'],
                  'user': configuracion['MYSQL_USER']}
    if configuracion['MYSQL_PASSWORD']:
        parametros['passwd'] = configuracion['MYSQL_PASSWORD']
    conexion = MySQLdb.connect(**parametros)
    try:
        conexion.cursor().execute(f'DROP DATABASE IF EXISTS `{BD_PRUEBAS}`')
    finally:
        conexion.close()


def test_endpoint_del_video_con_mysql(app_mysql):
    datos = app_mysql.test_client().get('/cursos').get_json()
    assert datos['mensaje'] == 'Éxito'
    assert len(datos['cursos']) == 12
    assert datos['cursos'][0] == {'codigo': 'ALG201', 'nombre': 'Algoritmos y Estructuras de Datos',
                                  'creditos': 5}


def test_crud_completo_con_mysql(app_mysql, curso_valido):
    cliente = app_mysql.test_client()
    assert cliente.post('/api/cursos', json=curso_valido).status_code == 201

    curso_valido.pop('codigo')
    curso_valido['modalidad'] = 'Híbrida'
    respuesta = cliente.put('/api/cursos/IAR401', json=curso_valido)
    assert respuesta.status_code == 200
    assert respuesta.get_json()['modalidad'] == 'Híbrida'
    # Repetir la actualización con los mismos datos también debe funcionar
    # (MySQL informa 0 filas modificadas en ese caso).
    assert cliente.put('/api/cursos/IAR401', json=curso_valido).status_code == 200

    assert cliente.delete('/api/cursos/IAR401').status_code == 200
    assert cliente.get('/api/cursos/IAR401').status_code == 404


def test_estadisticas_con_mysql(app_mysql):
    datos = app_mysql.test_client().get('/api/estadisticas').get_json()
    assert datos['total_cursos'] == 12
    assert datos['total_creditos'] == 44
    assert datos['promedio_creditos'] == 3.67


def test_paginas_html_con_mysql(app_mysql):
    cliente = app_mysql.test_client()
    assert '12 cursos encontrados' in cliente.get('/gestion/cursos/').get_data(as_text=True)
    assert 'Lucía Ramírez Soto' in cliente.get('/gestion/cursos/WEB201').get_data(as_text=True)
    assert 'Cursos registrados' in cliente.get('/').get_data(as_text=True)
