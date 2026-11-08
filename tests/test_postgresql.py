"""
Pruebas de integración con PostgreSQL (opcionales).

Solo se ejecutan si se define la variable de entorno PRUEBAS_POSTGRESQL=1 y hay
un servidor disponible con las credenciales POSTGRES_* del archivo .env.
Utilizan una base de datos aparte (por defecto «tarea_flask_pruebas») que se
crea y se elimina automáticamente, por lo que nunca modifican la base
«Tarea_Flask» real.

    PowerShell:   $env:PRUEBAS_POSTGRESQL="1"; python -m pytest -m postgresql -v
    Linux/macOS:  PRUEBAS_POSTGRESQL=1 python -m pytest -m postgresql -v
"""
import os

import pytest

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.skipif(os.getenv('PRUEBAS_POSTGRESQL') != '1',
                       reason='Defina PRUEBAS_POSTGRESQL=1 para ejecutar las pruebas con PostgreSQL.'),
]

BD_PRUEBAS = os.getenv('POSTGRES_DB_PRUEBAS', 'tarea_flask_pruebas')


@pytest.fixture()
def app_postgresql():
    import psycopg
    from psycopg import sql

    import database
    from app import create_app

    if BD_PRUEBAS.lower() == os.getenv('POSTGRES_DB', 'Tarea_Flask').lower():
        pytest.skip('La base de pruebas no puede ser la misma que la base real.')

    aplicacion = create_app('pruebas', DB_MOTOR='postgresql', POSTGRES_DB=BD_PRUEBAS)
    with aplicacion.app_context():
        database.inicializar_bd()  # Tabla y 12 cursos de ejemplo desde cero.

    yield aplicacion

    database.cerrar_pool(aplicacion)  # Libera las conexiones antes de borrar la base.
    parametros = database._parametros_postgresql(aplicacion.config, base='postgres')
    with psycopg.connect(**parametros, autocommit=True) as administrador:
        administrador.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)')
                              .format(sql.Identifier(BD_PRUEBAS)))


def test_endpoint_del_video_con_postgresql(app_postgresql):
    datos = app_postgresql.test_client().get('/cursos').get_json()
    assert datos['mensaje'] == 'Éxito'
    assert len(datos['cursos']) == 12
    assert datos['cursos'][0] == {'codigo': 'ALG201', 'nombre': 'Algoritmos y Estructuras de Datos',
                                  'creditos': 5}


def test_crud_completo_con_postgresql(app_postgresql, curso_valido):
    cliente = app_postgresql.test_client()
    assert cliente.post('/api/cursos', json=curso_valido).status_code == 201
    assert cliente.post('/api/cursos', json=curso_valido).status_code == 409   # clave primaria

    curso_valido.pop('codigo')
    curso_valido['modalidad'] = 'Híbrida'
    respuesta = cliente.put('/api/cursos/IAR401', json=curso_valido)
    assert respuesta.status_code == 200
    assert respuesta.get_json()['modalidad'] == 'Híbrida'

    assert cliente.delete('/api/cursos/IAR401').status_code == 200
    assert cliente.get('/api/cursos/IAR401').status_code == 404


def test_estadisticas_con_postgresql(app_postgresql):
    datos = app_postgresql.test_client().get('/api/estadisticas').get_json()
    assert datos['total_cursos'] == 12
    assert datos['total_creditos'] == 44
    assert datos['promedio_creditos'] == 3.67


def test_paginas_html_con_postgresql(app_postgresql):
    cliente = app_postgresql.test_client()
    assert '12 cursos encontrados' in cliente.get('/gestion/cursos/').get_data(as_text=True)
    assert 'Lucía Ramírez Soto' in cliente.get('/gestion/cursos/WEB201').get_data(as_text=True)
    html = cliente.get('/').get_data(as_text=True)
    assert 'Cursos registrados' in html
    assert 'Base de datos: <strong>PostgreSQL</strong>' in html


def test_busqueda_sin_distinguir_mayusculas_con_postgresql(app_postgresql):
    cliente = app_postgresql.test_client()
    # En PostgreSQL LIKE distingue mayúsculas; la aplicación usa ILIKE.
    html = cliente.get('/gestion/cursos/?q=FLASK').get_data(as_text=True)
    assert '1 curso encontrado para «FLASK»' in html
    assert cliente.get('/api/cursos?q=python').get_json()['total'] == 1
