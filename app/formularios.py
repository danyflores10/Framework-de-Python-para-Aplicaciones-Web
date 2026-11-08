"""
formularios.py
==============
Formularios web definidos con Flask-WTF (WTForms).

Cada campo declara sus propias reglas de validación, que se ejecutan en el
servidor. Flask-WTF añade además un token CSRF oculto a cada formulario para
impedir que otro sitio envíe datos en nombre del usuario.
"""
from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, Regexp

from modelos.curso import Curso


def _limpiar(valor):
    """Filtro: elimina los espacios sobrantes al inicio y al final del texto."""
    return valor.strip() if isinstance(valor, str) else valor


def _mayusculas(valor):
    """Filtro: normaliza el código del curso en mayúsculas (web201 -> WEB201)."""
    return valor.strip().upper() if isinstance(valor, str) else valor


class FormularioBase(FlaskForm):
    """Formulario base con los mensajes internos de WTForms en español."""

    class Meta:
        locales = ('es_ES', 'es')


class CursoFormulario(FormularioBase):
    """Datos de un curso. Se usa para registrar, editar y en la API REST."""

    codigo = StringField('Código', filters=[_mayusculas], validators=[
        DataRequired(message='El código es obligatorio.'),
        Regexp(r'^[A-Z]{3}[0-9]{3}$',
               message='Use 3 letras seguidas de 3 números (por ejemplo, WEB201).'),
    ])
    nombre = StringField('Nombre del curso', filters=[_limpiar], validators=[
        DataRequired(message='El nombre del curso es obligatorio.'),
        Length(min=3, max=80, message='El nombre debe tener entre 3 y 80 caracteres.'),
    ])
    creditos = IntegerField('Créditos', validators=[
        InputRequired(message='Indique el número de créditos.'),
        NumberRange(min=1, max=10, message='Los créditos deben estar entre 1 y 10.'),
    ])
    docente = StringField('Docente', filters=[_limpiar], validators=[
        DataRequired(message='El nombre del docente es obligatorio.'),
        Length(min=3, max=80, message='El nombre del docente debe tener entre 3 y 80 caracteres.'),
    ])
    modalidad = SelectField('Modalidad', choices=[(m, m) for m in Curso.MODALIDADES], validators=[
        DataRequired(message='Seleccione una modalidad.'),
    ])
    descripcion = TextAreaField('Descripción', filters=[_limpiar], validators=[
        Optional(),
        Length(max=500, message='La descripción admite como máximo 500 caracteres.'),
    ])
    enviar = SubmitField('Guardar curso')

    def datos_curso(self):
        """Devuelve un diccionario con los datos limpios y validados del curso."""
        datos = {
            'nombre': self.nombre.data,
            'creditos': self.creditos.data,
            'docente': self.docente.data,
            'modalidad': self.modalidad.data,
            'descripcion': self.descripcion.data or None,
        }
        if 'codigo' in self:          # Al editar, el campo «codigo» se elimina.
            datos['codigo'] = self.codigo.data
        return datos


class ContactoFormulario(FormularioBase):
    """Formulario que genera la URL dinámica /contacto/<nombre>/<int:edad>."""

    nombre = StringField('Nombre', filters=[_limpiar], validators=[
        DataRequired(message='Escriba su nombre.'),
        Length(min=2, max=40, message='El nombre debe tener entre 2 y 40 caracteres.'),
        Regexp(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' ]+$", message='Use solo letras y espacios.'),
    ])
    edad = IntegerField('Edad', validators=[
        InputRequired(message='Escriba su edad.'),
        NumberRange(min=1, max=120, message='La edad debe estar entre 1 y 120 años.'),
    ])
    enviar = SubmitField('Generar URL dinámica')
