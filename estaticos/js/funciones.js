// Estados de la aplicación
const ESTADOS = {
    INICIAL: 'inicial',
    LLAMADA_ACTIVA: 'llamada_activa',
    GRABANDO: 'grabando',
    FINALIZADO: 'finalizado'
};

// Variables globales
let estadoActual = ESTADOS.INICIAL;
let dispositivoSeleccionado = false;
let clienteSeleccionado = false;
let grabando = false;

// Base de datos simulada de clientes
const CLIENTES = {
    '1': {
        nombre: 'Luis Guillermo Pardo',
        tipologia: 'Jurídica',
        deuda: 100,
        documento: '123456789',
        email: 'luis.pardo@ejemplo.com',
        telefono: '3001234567'
    },
    '2': {
        nombre: 'María Rodríguez',
        tipologia: 'Natural',
        deuda: 500,
        documento: '987654321',
        email: 'maria.rodriguez@ejemplo.com',
        telefono: '3109876543'
    },
    '3': {
        nombre: 'Carlos Ramírez',
        tipologia: 'Jurídica',
        deuda: 1500,
        documento: '456789123',
        email: 'carlos.ramirez@ejemplo.com',
        telefono: '3158765432'
    }
};

// Cargar dispositivos de audio
async function cargarDispositivos() {
    try {
        const response = await fetch('/dispositivos');
        const dispositivos = await response.json();
        const selector = document.getElementById('selectorDispositivo');
        selector.innerHTML = '<option value="">Seleccione un micrófono...</option>';
        
        dispositivos.forEach(dispositivo => {
            const option = document.createElement('option');
            option.value = dispositivo.id;
            option.textContent = dispositivo.nombre;
            selector.appendChild(option);
        });
    } catch (error) {
        console.error('Error al cargar dispositivos:', error);
        agregarMensaje('Sistema: Error al cargar dispositivos de audio');
    }
}

// Actualizar información del cliente
async function actualizarInformacionCliente(idCliente) {
    try {
        const cliente = CLIENTES[idCliente];
        if (cliente) {
            document.getElementById('nombreCliente').textContent = cliente.nombre;
            document.getElementById('tipologiaCliente').textContent = cliente.tipologia;
            document.getElementById('deudaCliente').textContent = cliente.deuda;
            document.getElementById('infoAdicional').innerHTML = `
                <div class="info-detalle">Documento: ${cliente.documento}</div>
                <div class="info-detalle">Email: ${cliente.email}</div>
                <div class="info-detalle">Teléfono: ${cliente.telefono}</div>
            `;
            clienteSeleccionado = true;
            actualizarEstadoUI();
            agregarMensaje(`Sistema: Cliente ${cliente.nombre} seleccionado`);
        }
    } catch (error) {
        console.error('Error al cargar información del cliente:', error);
        agregarMensaje('Sistema: Error al cargar información del cliente');
    }
}

// Configurar dispositivo de audio
async function configurarDispositivo(idDispositivo) {
    try {
        const response = await fetch('/configurar_dispositivo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_dispositivo: parseInt(idDispositivo) })
        });
        const data = await response.json();
        dispositivoSeleccionado = data.exito;
        actualizarEstadoUI();
        if (data.exito) {
            agregarMensaje('Sistema: Micrófono configurado correctamente');
        }
    } catch (error) {
        console.error('Error al configurar dispositivo:', error);
        agregarMensaje('Sistema: Error al configurar micrófono');
    }
}

// Actualizar estado de la UI
function actualizarEstadoUI() {
    const btnLlamada = document.getElementById('btnLlamada');
    const btnGrabacion = document.getElementById('btnGrabacion');
    const btnFinalizar = document.getElementById('btnFinalizar');
    const estadoLlamada = document.getElementById('estadoLlamada');
    const selectorMicrofono = document.getElementById('selectorDispositivo');
    const selectorCliente = document.getElementById('selectorCliente');

    // Deshabilitar selectores durante la llamada
    selectorMicrofono.disabled = estadoActual !== ESTADOS.INICIAL;
    selectorCliente.disabled = estadoActual !== ESTADOS.INICIAL;

    // Actualizar texto del botón de grabación
    btnGrabacion.textContent = grabando ? '⏹️ Detener Grabación' : '🎙️ Iniciar Grabación';

    switch(estadoActual) {
        case ESTADOS.INICIAL:
            btnLlamada.disabled = !dispositivoSeleccionado || !clienteSeleccionado;
            btnGrabacion.disabled = true;
            btnFinalizar.disabled = true;
            estadoLlamada.textContent = !clienteSeleccionado ? 
                'Seleccione un cliente' : 
                (!dispositivoSeleccionado ? 'Seleccione un micrófono' : 'Listo para iniciar llamada');
            break;

        case ESTADOS.LLAMADA_ACTIVA:
            btnLlamada.disabled = true;
            btnGrabacion.disabled = false;
            btnFinalizar.disabled = false;
            estadoLlamada.textContent = 'Llamada en curso';
            break;

        case ESTADOS.GRABANDO:
            btnLlamada.disabled = true;
            btnGrabacion.disabled = false;
            btnFinalizar.disabled = true;
            estadoLlamada.textContent = 'Grabando...';
            break;

        case ESTADOS.FINALIZADO:
            btnLlamada.disabled = false;
            btnGrabacion.disabled = true;
            btnFinalizar.disabled = true;
            estadoLlamada.textContent = 'Llamada finalizada';
            grabando = false;
            break;
    }
}

// Agregar mensaje al área de transcripción
function agregarMensaje(texto) {
    const areaTranscripcion = document.getElementById('areaTranscripcion');
    const tiempo = new Date().toLocaleTimeString();
    const nuevoMensaje = document.createElement('div');
    nuevoMensaje.className = 'mensaje-transcripcion';
    nuevoMensaje.textContent = `[${tiempo}] ${texto}`;
    areaTranscripcion.insertBefore(nuevoMensaje, areaTranscripcion.firstChild);
}

// Manejar inicio de llamada
async function iniciarLlamada() {
    estadoActual = ESTADOS.LLAMADA_ACTIVA;
    agregarMensaje('Sistema: Llamada iniciada con el cliente');
    actualizarEstadoUI();
}

// Manejar grabación
async function manejarGrabacion() {
    try {
        if (!grabando) {
            const response = await fetch('/iniciar', { method: 'POST' });
            const data = await response.json();
            
            if (data.exito) {
                grabando = true;
                estadoActual = ESTADOS.GRABANDO;
                actualizarEstadoUI();
                agregarMensaje('Sistema: Grabación iniciada');
            }
        } else {
            const response = await fetch('/detener', { method: 'POST' });
            const data = await response.json();
            
            grabando = false;
            estadoActual = ESTADOS.LLAMADA_ACTIVA;
            actualizarEstadoUI();
            
            if (data.transcripcion) {
                agregarMensaje(`Cliente: ${data.transcripcion}`);
                actualizarAnalisis();
            }
            agregarMensaje('Sistema: Grabación detenida');
        }
    } catch (error) {
        console.error('Error al manejar grabación:', error);
        agregarMensaje('Sistema: Error en la grabación');
        grabando = false;
        actualizarEstadoUI();
    }
}

// Finalizar llamada
function finalizarLlamada() {
    if (grabando) {
        manejarGrabacion();
    }
    estadoActual = ESTADOS.FINALIZADO;
    agregarMensaje('Sistema: Llamada finalizada');
    mostrarAnalisisFinal();
    actualizarEstadoUI();
}

// Actualizar análisis durante la llamada
function actualizarAnalisis() {
    document.getElementById('emociones').innerHTML = `
        <p><strong>Análisis en tiempo real:</strong></p>
        <p>Tono: Neutral</p>
        <p>Frustración: Baja</p>
        <p>Cooperación: Alta</p>
    `;
    
    document.getElementById('exito').innerHTML = `
        <p><strong>Progreso:</strong></p>
        <p>Probabilidad de acuerdo: 75%</p>
        <p>Disposición al pago: Positiva</p>
    `;
    
    document.getElementById('costos').innerHTML = `
        <p><strong>Costos actuales:</strong></p>
        <p>Duración: ${Math.floor(Math.random() * 5) + 1}:${Math.floor(Math.random() * 60).toString().padStart(2, '0')}</p>
        <p>Costo: $${(Math.random() * 5 + 1).toFixed(2)}</p>
    `;
}

// Mostrar análisis final
function mostrarAnalisisFinal() {
    document.getElementById('emociones').innerHTML = `
        <p><strong>Análisis Final:</strong></p>
        <p>Tono predominante: Colaborativo</p>
        <p>Frustración inicial: Media</p>
        <p>Frustración final: Baja</p>
    `;
    
    document.getElementById('exito').innerHTML = `
        <p><strong>Resultado:</strong></p>
        <p>Acuerdo alcanzado: Sí</p>
        <p>Plan de pagos establecido</p>
        <p>Probabilidad de cumplimiento: 85%</p>
    `;
    
    document.getElementById('costos').innerHTML = `
        <p><strong>Costos Finales:</strong></p>
        <p>Duración total: 6:23</p>
        <p>Costo llamada: $3.50</p>
        <p>Procesamiento IA: $1.73</p>
        <p>Total: $5.23</p>
    `;
}

// Configurar eventos cuando el documento esté listo
document.addEventListener('DOMContentLoaded', () => {
    // Cargar dispositivos
    cargarDispositivos();
    
    // Configurar eventos
    document.getElementById('selectorCliente').addEventListener('change', (e) => {
        if (e.target.value) {
            actualizarInformacionCliente(e.target.value);
        }
    });
    
    document.getElementById('selectorDispositivo').addEventListener('change', (e) => {
        if (e.target.value) {
            configurarDispositivo(e.target.value);
        }
    });
    
    document.getElementById('btnLlamada').addEventListener('click', iniciarLlamada);
    document.getElementById('btnGrabacion').addEventListener('click', manejarGrabacion);
    document.getElementById('btnFinalizar').addEventListener('click', finalizarLlamada);
    
    // Inicializar estado
    actualizarEstadoUI();
});