"""
conftest.py
===========
Configuración compartida de pytest.

Cada prueba recibe una aplicación nueva con su propia base de datos SQLite
temporal; así las pruebas son independientes entre sí y nunca modifican los
datos reales del proyecto.
"""
import sys
from pathlib import Path

import pytest

# Los módulos de la aplicación están dentro de la carpeta «app» (como en el video).
DIRECTORIO_APP = Path(__file__).resolve().parents[1] / 'app'
sys.path.insert(0, str(DIRECTORIO_APP))

from app import create_app  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    """Aplicación en modo de pruebas con una base SQLite temporal (12 cursos)."""
    return create_app('pruebas', SQLITE_PATH=str(tmp_path / 'abaco_pruebas.db'))


@pytest.fixture()
def cliente(app):
    """Cliente HTTP de pruebas de Flask: simula las peticiones de un navegador."""
    return app.test_client()


@pytest.fixture()
def curso_valido():
    """Datos de un curso nuevo que cumple todas las validaciones."""
    return {
        'codigo': 'IAR401',
        'nombre': 'Inteligencia Artificial',
        'creditos': 4,
        'docente': 'Elena Castro Ruiz',
        'modalidad': 'Virtual',
        'descripcion': 'Aprendizaje automático y redes neuronales con Python.',
    }
