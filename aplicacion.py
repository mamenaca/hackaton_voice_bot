from flask import Flask, jsonify, request, render_template
from modulos.procesador_audio import ProcesadorAudio
import webbrowser
from threading import Timer
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicialización de Flask con las rutas de carpetas
app = Flask(__name__, 
    template_folder='plantillas',
    static_folder='estaticos')

# Inicialización del procesador de audio
procesador = ProcesadorAudio()

# Base de datos simulada de clientes
CLIENTES = {
    1: {
        'id': 1,
        'nombre': 'Luis Guillermo Pardo',
        'tipologia': 'Jurídica',
        'deuda': 100,
        'documento': '123456789',
        'telefono': '3001234567',
        'email': 'luis.pardo@ejemplo.com',
        'fecha_vencimiento': '2024-12-31',
        'estado_cuenta': 'En mora',
        'historial_pagos': [
            {'fecha': '2024-01-15', 'monto': 50},
            {'fecha': '2024-02-15', 'monto': 30}
        ]
    },
    2: {
        'id': 2,
        'nombre': 'María Rodríguez',
        'tipologia': 'Natural',
        'deuda': 500,
        'documento': '987654321',
        'telefono': '3109876543',
        'email': 'maria.rodriguez@ejemplo.com',
        'fecha_vencimiento': '2024-11-30',
        'estado_cuenta': 'Pendiente',
        'historial_pagos': [
            {'fecha': '2024-01-20', 'monto': 100}
        ]
    },
    3: {
        'id': 3,
        'nombre': 'Carlos Ramírez',
        'tipologia': 'Jurídica',
        'deuda': 1500,
        'documento': '456789123',
        'telefono': '3158765432',
        'email': 'carlos.ramirez@ejemplo.com',
        'fecha_vencimiento': '2024-10-15',
        'estado_cuenta': 'En mora',
        'historial_pagos': [
            {'fecha': '2024-01-10', 'monto': 200},
            {'fecha': '2024-02-10', 'monto': 150}
        ]
    }
}

# Rutas de la aplicación
@app.route('/')
def inicio():
    """Ruta principal que renderiza la plantilla inicial"""
    logger.info("Acceso a la página principal")
    return render_template('inicio.html')

@app.route('/dispositivos')
def obtener_dispositivos():
    """Obtiene la lista de dispositivos de audio disponibles"""
    logger.info("Solicitando lista de dispositivos de audio")
    try:
        dispositivos = procesador.obtener_dispositivos_entrada()
        return jsonify(dispositivos)
    except Exception as e:
        logger.error(f"Error al obtener dispositivos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/configurar_dispositivo', methods=['POST'])
def configurar_dispositivo():
    """Configura el dispositivo de audio seleccionado"""
    try:
        datos = request.json
        id_dispositivo = datos.get('id_dispositivo')
        logger.info(f"Configurando dispositivo de audio: {id_dispositivo}")
        
        exito = procesador.configurar_dispositivo_entrada(id_dispositivo)
        return jsonify({"exito": exito})
    except Exception as e:
        logger.error(f"Error al configurar dispositivo: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/iniciar', methods=['POST'])
def iniciar_grabacion():
    """Inicia la grabación de audio"""
    try:
        logger.info("Iniciando grabación de audio")
        exito = procesador.iniciar_grabacion()
        return jsonify({
            "exito": exito,
            "estado": "Grabación iniciada" if exito else "Error al iniciar grabación"
        })
    except Exception as e:
        logger.error(f"Error al iniciar grabación: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/detener', methods=['POST'])
def detener_grabacion():
    """Detiene la grabación y procesa el audio"""
    try:
        logger.info("Deteniendo grabación de audio")
        texto = procesador.detener_grabacion()
        return jsonify({
            "estado": "Grabación detenida",
            "transcripcion": texto
        })
    except Exception as e:
        logger.error(f"Error al detener grabación: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/cliente/<int:id_cliente>')
def obtener_cliente(id_cliente):
    """Obtiene la información de un cliente específico"""
    try:
        logger.info(f"Solicitando información del cliente {id_cliente}")
        cliente = CLIENTES.get(id_cliente)
        if cliente:
            return jsonify(cliente)
        return jsonify({'error': 'Cliente no encontrado'}), 404
    except Exception as e:
        logger.error(f"Error al obtener cliente: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/actualizar_estado/<int:id_cliente>', methods=['POST'])
def actualizar_estado_cliente(id_cliente):
    """Actualiza el estado de un cliente"""
    try:
        datos = request.json
        nuevo_estado = datos.get('estado')
        if id_cliente in CLIENTES and nuevo_estado:
            CLIENTES[id_cliente]['estado_cuenta'] = nuevo_estado
            logger.info(f"Estado del cliente {id_cliente} actualizado a: {nuevo_estado}")
            return jsonify({"exito": True})
        return jsonify({'error': 'Cliente no encontrado o estado no especificado'}), 404
    except Exception as e:
        logger.error(f"Error al actualizar estado del cliente: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/analisis/<int:id_cliente>')
def obtener_analisis(id_cliente):
    """Obtiene el análisis de la llamada para un cliente específico"""
    try:
        logger.info(f"Generando análisis para cliente {id_cliente}")
        return jsonify({
            "emociones": {
                "tono": "Neutral",
                "frustracion": "Baja",
                "cooperacion": "Alta"
            },
            "exito": {
                "probabilidad_acuerdo": 75,
                "disposicion_pago": "Positiva"
            },
            "costos": {
                "duracion": "5:30",
                "costo_llamada": 3.50,
                "procesamiento": 1.73,
                "total": 5.23
            }
        })
    except Exception as e:
        logger.error(f"Error al generar análisis: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Manejo de errores
@app.errorhandler(404)
def no_encontrado(error):
    return jsonify({'error': 'Ruta no encontrada'}), 404

@app.errorhandler(500)
def error_servidor(error):
    return jsonify({'error': 'Error interno del servidor'}), 500

def abrir_navegador():
    """Abre el navegador automáticamente al iniciar la aplicación"""
    webbrowser.open('http://127.0.0.1:5000')

# Inicialización de la aplicación
if __name__ == '__main__':
    logger.info("Iniciando aplicación VoiceBot")
    Timer(0.00000025, abrir_navegador).start()
    app.run(port=5000, debug=False)