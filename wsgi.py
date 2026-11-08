"""
wsgi.py
=======
Punto de entrada WSGI para ejecutar la aplicación con un servidor de
producción en lugar del servidor de desarrollo de Flask.

Ejemplo con Waitress (funciona en Windows, Linux y macOS):
    waitress-serve --listen=127.0.0.1:8000 wsgi:app
"""
import logging
import sys
from pathlib import Path

from flask.logging import default_handler

# La carpeta «app» contiene los módulos de la aplicación (igual que en el video).
sys.path.insert(0, str(Path(__file__).resolve().parent / 'app'))

from app import create_app  # noqa: E402

# Registro (logging) de producción con un único formato y sin mensajes duplicados.
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(levelname)s en %(name)s: %(message)s')

app = create_app('produccion')
app.logger.removeHandler(default_handler)
