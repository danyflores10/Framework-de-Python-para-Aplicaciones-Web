/*
 * api.js - Consola para probar la API REST desde el navegador.
 * Envía peticiones con fetch() y muestra el código de estado y el JSON recibido.
 */
document.addEventListener('DOMContentLoaded', () => {
    const formulario = document.getElementById('consola-api');
    if (!formulario) {
        return;
    }

    const metodo = document.getElementById('metodo');
    const ruta = document.getElementById('ruta');
    const cuerpo = document.getElementById('cuerpo');
    const estado = document.getElementById('respuesta-estado');
    const salida = document.getElementById('respuesta-cuerpo');

    // El cuerpo JSON solo se habilita para los métodos que lo necesitan.
    const actualizarCuerpo = () => {
        cuerpo.disabled = !['POST', 'PUT'].includes(metodo.value);
    };

    // Botones de ejemplo: cargan el método, la ruta y el cuerpo en la consola.
    document.querySelectorAll('[data-ejemplo]').forEach((boton) => {
        boton.addEventListener('click', () => {
            metodo.value = boton.dataset.metodo;
            ruta.value = boton.dataset.ruta;
            cuerpo.value = boton.dataset.cuerpo
                ? JSON.stringify(JSON.parse(boton.dataset.cuerpo), null, 2)
                : '';
            actualizarCuerpo();
        });
    });

    metodo.addEventListener('change', actualizarCuerpo);
    actualizarCuerpo();

    formulario.addEventListener('submit', async (evento) => {
        evento.preventDefault();
        const opciones = { method: metodo.value, headers: { Accept: 'application/json' } };
        if (!cuerpo.disabled && cuerpo.value.trim()) {
            opciones.headers['Content-Type'] = 'application/json';
            opciones.body = cuerpo.value;
        }

        estado.textContent = 'Enviando…';
        delete estado.dataset.ok;
        const inicio = performance.now();
        try {
            const respuesta = await fetch(ruta.value, opciones);
            const texto = await respuesta.text();
            let contenido = texto;
            try {
                contenido = JSON.stringify(JSON.parse(texto), null, 2);
            } catch (error) {
                // La respuesta no es JSON: se muestra tal cual.
            }
            const milisegundos = Math.round(performance.now() - inicio);
            estado.textContent = `${respuesta.status} ${respuesta.statusText} · ${milisegundos} ms`;
            estado.dataset.ok = String(respuesta.ok);
            salida.textContent = contenido;
        } catch (error) {
            estado.textContent = 'Error de red';
            estado.dataset.ok = 'false';
            salida.textContent = String(error);
        }
    });
});
