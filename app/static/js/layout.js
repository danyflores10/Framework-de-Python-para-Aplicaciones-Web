/*
 * layout.js - Comportamiento común de todas las páginas.
 * Se importa al final de layout.html con url_for('static', filename='js/layout.js').
 */

// alert('Hola Mundo!!!');  // Prueba de importación utilizada en el video.

document.addEventListener('DOMContentLoaded', () => {
    // 1. Menú desplegable en pantallas pequeñas.
    const botonMenu = document.querySelector('[data-menu]');
    const navegacion = document.getElementById('navegacion');
    if (botonMenu && navegacion) {
        botonMenu.addEventListener('click', () => {
            const abierta = navegacion.classList.toggle('abierta');
            botonMenu.setAttribute('aria-expanded', String(abierta));
        });
    }

    // 2. Botón para cerrar los mensajes flash.
    document.querySelectorAll('.alerta').forEach((alerta) => {
        const cerrar = alerta.querySelector('.alerta__cerrar');
        if (!cerrar) {
            return;
        }
        cerrar.addEventListener('click', () => {
            alerta.classList.add('alerta--oculta');
            window.setTimeout(() => alerta.remove(), 300);
        });
    });

    // 3. Confirmación antes de enviar formularios peligrosos (eliminar).
    document.querySelectorAll('form[data-confirmar]').forEach((formulario) => {
        formulario.addEventListener('submit', (evento) => {
            if (!window.confirm(formulario.dataset.confirmar)) {
                evento.preventDefault();
            }
        });
    });

    // 4. Contador de caracteres para los campos de texto con límite.
    document.querySelectorAll('textarea[maxlength]').forEach((campo) => {
        const contador = document.createElement('small');
        contador.className = 'campo__ayuda';
        const actualizar = () => {
            contador.textContent = `${campo.value.length} / ${campo.maxLength} caracteres`;
        };
        campo.insertAdjacentElement('afterend', contador);
        campo.addEventListener('input', actualizar);
        actualizar();
    });
});
