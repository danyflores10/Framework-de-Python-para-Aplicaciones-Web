"""
modelos/curso.py
================
Modelo «Curso»: reúne todas las sentencias SQL que trabajan con la tabla
``curso`` (la misma tabla que se consulta en el video tutorial).

Las vistas (rutas) nunca escriben SQL: llaman a los métodos de esta clase.
Así se respeta la separación de responsabilidades del patrón MVC.
"""
from datetime import datetime

from database import consultar, ejecutar, operador_busqueda


class Curso:
    """Operaciones CRUD (crear, leer, actualizar y eliminar) sobre «curso»."""

    MODALIDADES = ('Presencial', 'Virtual', 'Híbrida')

    # Lista blanca de columnas por las que se permite ordenar. Los nombres de
    # columna no pueden enviarse como parámetros SQL, por eso se validan aquí.
    COLUMNAS_ORDEN = ('codigo', 'nombre', 'creditos', 'docente', 'modalidad', 'fecha_registro')

    CAMPOS = 'codigo, nombre, creditos, docente, modalidad, descripcion, fecha_registro'

    @staticmethod
    def _filtros(busqueda='', modalidad=''):
        """Construye la cláusula WHERE y sus parámetros a partir de los filtros."""
        condiciones, parametros = [], []
        if busqueda:
            patron = f'%{busqueda}%'
            like = operador_busqueda()  # ILIKE en PostgreSQL, LIKE en MySQL y SQLite
            condiciones.append(f'(codigo {like} %s OR nombre {like} %s OR docente {like} %s)')
            parametros.extend([patron, patron, patron])
        if modalidad:
            condiciones.append('modalidad = %s')
            parametros.append(modalidad)
        where = f" WHERE {' AND '.join(condiciones)}" if condiciones else ''
        return where, parametros

    @staticmethod
    def listar_basico():
        """Consulta exacta del video: código, nombre y créditos ordenados por nombre."""
        return consultar('SELECT codigo, nombre, creditos FROM curso ORDER BY nombre ASC')

    @classmethod
    def listar(cls, busqueda='', modalidad='', orden='nombre', direccion='asc',
               limite=None, desplazamiento=0):
        """Devuelve los cursos filtrados, ordenados y (opcionalmente) paginados."""
        if orden not in cls.COLUMNAS_ORDEN:
            orden = 'nombre'
        direccion = 'DESC' if str(direccion).lower() == 'desc' else 'ASC'
        where, parametros = cls._filtros(busqueda, modalidad)
        sql = f'SELECT {cls.CAMPOS} FROM curso{where} ORDER BY {orden} {direccion}, codigo ASC'
        if limite is not None:
            sql += ' LIMIT %s OFFSET %s'
            parametros.extend([int(limite), int(desplazamiento)])
        return consultar(sql, parametros)

    @classmethod
    def contar(cls, busqueda='', modalidad=''):
        """Cantidad de cursos que cumplen los filtros (se usa para paginar)."""
        where, parametros = cls._filtros(busqueda, modalidad)
        fila = consultar(f'SELECT COUNT(*) AS total FROM curso{where}', parametros, uno=True)
        return int(fila['total'])

    @classmethod
    def obtener(cls, codigo):
        """Busca un curso por su código (clave primaria). Devuelve None si no existe."""
        return consultar(f'SELECT {cls.CAMPOS} FROM curso WHERE codigo = %s',
                         (str(codigo).strip().upper(),), uno=True)

    @staticmethod
    def crear(datos):
        """Inserta un curso nuevo. ``datos`` proviene de un formulario ya validado."""
        ejecutar(
            'INSERT INTO curso (codigo, nombre, creditos, docente, modalidad, descripcion, '
            'fecha_registro) VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (
                datos['codigo'], datos['nombre'], datos['creditos'], datos['docente'],
                datos['modalidad'], datos.get('descripcion') or None,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ),
        )

    @staticmethod
    def actualizar(codigo, datos):
        """Actualiza los datos de un curso existente (el código no cambia)."""
        ejecutar(
            'UPDATE curso SET nombre = %s, creditos = %s, docente = %s, modalidad = %s, '
            'descripcion = %s WHERE codigo = %s',
            (
                datos['nombre'], datos['creditos'], datos['docente'], datos['modalidad'],
                datos.get('descripcion') or None, codigo,
            ),
        )

    @staticmethod
    def eliminar(codigo):
        """Elimina un curso. Devuelve True si se borró algún registro."""
        return ejecutar('DELETE FROM curso WHERE codigo = %s', (codigo,)) > 0

    @staticmethod
    def estadisticas():
        """Indicadores generales para la página de inicio y la API."""
        resumen = consultar(
            'SELECT COUNT(*) AS total, COALESCE(SUM(creditos), 0) AS creditos, '
            'COALESCE(AVG(creditos), 0) AS promedio FROM curso',
            uno=True,
        )
        por_modalidad = consultar(
            'SELECT modalidad, COUNT(*) AS cantidad FROM curso '
            'GROUP BY modalidad ORDER BY cantidad DESC, modalidad ASC'
        )
        # MySQL devuelve SUM y AVG como Decimal: se convierten a int y float.
        return {
            'total_cursos': int(resumen['total']),
            'total_creditos': int(resumen['creditos']),
            'promedio_creditos': round(float(resumen['promedio']), 2),
            'por_modalidad': [
                {'modalidad': fila['modalidad'], 'cantidad': int(fila['cantidad'])}
                for fila in por_modalidad
            ],
        }
