import sounddevice as sd
import numpy as np
import wave
import google.generativeai as genai
from flask import Flask, jsonify, request, render_template_string
import base64
import threading
import queue
import time
import logging
import webbrowser
from threading import Timer
import os  # Agregamos esta importación

class AudioProcessor:
    def __init__(self):
        # Primero inicializamos el logger
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Ajustes de audio mejorados
        self.sample_rate = 16000  # Reducido de 44100 a 16000 Hz
        self.channels = 1         # Mono
        self.chunk_size = 1024    # Reducido para mejor manejo
        self.dtype = np.int16     # Tipo de datos específico
        self.selected_device = None
        
        # Luego inicializamos el resto de atributos
        self.api_keys = [
            "AIzaSyBhnvqxLjhzfbUp3MnFjwEMsNJ4VYY7r3A",
            "AIzaSyB5wvYrrT1DzA4bH4oRLuO0lF4TS3fMiw8",
            "AIzaSyDKj4QW99q9Kfvues0AtSmGRGNqhYrUr7A",
            "AIzaSyCIt5-vZ45sYP-VlEF98fFbpZAbWOmdNz0",
            "AIzaSyDKzJgxKgHo8mOZ7pJueCRW57x0OQYObBY",
            "AIzaSyD9Bu2jX6jXbuuaTW2Sjh4hhUeuJdYD23s"
        ]
        self.api_key_index = 0
        self.audio_queue = queue.Queue()
        self.is_recording = False
        
        self.sample_rate = 44100
        self.channels = 1
        self.chunk_size = 1024 * 2
        self.selected_device = None

        # Finalmente configuramos Gemini
        self.genai_model = self.setup_genai()
        
    def setup_genai(self):
        """Configura el cliente de Gemini API con la API key actual"""
        try:
            genai.configure(api_key=self.api_keys[self.api_key_index])
            model = genai.GenerativeModel('gemini-1.5-flash')
            self.logger.info("Gemini API configurada exitosamente")
            return model
        except Exception as e:
            self.logger.error(f"Error configurando Gemini API: {str(e)}")
            return None

    def rotate_api_key(self):
        """Rota a la siguiente API key disponible"""
        self.api_key_index = (self.api_key_index + 1) % len(self.api_keys)
        self.genai_model = self.setup_genai()
        self.logger.info(f"Rotated to API key index: {self.api_key_index}")

    def get_input_devices(self):
        """Obtiene lista de dispositivos de entrada de audio"""
        devices = sd.query_devices()
        input_devices = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # Es un dispositivo de entrada
                input_devices.append({
                    'id': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'default_samplerate': device['default_samplerate']
                })
        return input_devices

    def set_input_device(self, device_id):
        """Configura el dispositivo de entrada con parámetros optimizados"""
        try:
            device_info = sd.query_devices(device_id, 'input')
            self.selected_device = device_id
            
            # Usar la tasa de muestreo nativa del dispositivo si es posible
            suggested_rate = int(device_info['default_samplerate'])
            if 16000 <= suggested_rate <= 48000:
                self.sample_rate = suggested_rate
            else:
                self.sample_rate = 16000  # Fallback a 16kHz
                
            self.channels = 1  # Mantener mono para mejor calidad
            self.logger.info(f"Dispositivo configurado: {device_info['name']} @ {self.sample_rate}Hz")
            return True
        except Exception as e:
            self.logger.error(f"Error configurando dispositivo: {str(e)}")
            return False

    def audio_callback(self, indata, frames, time, status):
        """Callback para procesar el audio entrante"""
        if status:
            self.logger.warning(f"Audio callback status: {status}")
        self.audio_queue.put(indata.copy())
        self.logger.debug(f"Audio recibido: {indata.shape} frames")

    def save_audio(self, frames, filename="temp_audio.wav"):
        """Guarda los frames de audio con configuración optimizada"""
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16 bits por muestra
                wf.setframerate(self.sample_rate)
                wf.writeframes(frames.tobytes())
            
            file_size = os.path.getsize(filename)
            self.logger.info(f"Archivo de audio guardado: {filename} ({file_size} bytes)")
            return filename
        except Exception as e:
            self.logger.error(f"Error guardando audio: {str(e)}")
            return None

    def transcribe_audio(self, audio_file):
        """Transcribe el audio usando Gemini API"""
        try:
            if not os.path.exists(audio_file):
                self.logger.error(f"El archivo de audio no existe: {audio_file}")
                return None

            with open(audio_file, 'rb') as f:
                audio_bytes = f.read()
            
            self.logger.info(f"Tamaño del audio en bytes: {len(audio_bytes)}")
            
            audio_b64 = base64.b64encode(audio_bytes).decode()
            

            audio_file = genai.upload_file(path="temp_audio.wav")

            prompt = ["Transcribe el siguiente audio en español: .",audio_file]
            self.logger.debug(f"Enviando prompt a Gemini: {prompt[:100]}...")
            
            response = self.genai_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=200,
                    temperature=0.2,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            self.logger.info(f"Respuesta recibida de Gemini: {response.text}")
            return response.text
            
        except Exception as e:
            self.logger.error(f"Error en transcripción: {str(e)}")
            self.rotate_api_key()
            return f"Error en transcripción: {str(e)}"

    def start_recording(self):
        """Inicia la grabación de audio con parámetros optimizados"""
        if self.selected_device is None:
            self.logger.error("No se ha seleccionado dispositivo de entrada")
            return False
        
        self.logger.info(f"Iniciando grabación con dispositivo {self.selected_device}...")
        self.is_recording = True
        self.audio_queue = queue.Queue()
        
        def record_audio():
            try:
                with sd.InputStream(
                    callback=self.audio_callback,
                    device=self.selected_device,
                    channels=self.channels,
                    samplerate=self.sample_rate,
                    dtype=self.dtype,
                    blocksize=self.chunk_size,
                    latency='low'  # Reducir latencia
                ):
                    self.logger.info("Stream de audio iniciado")
                    while self.is_recording:
                        time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error en grabación: {str(e)}")
        
        self.recording_thread = threading.Thread(target=record_audio)
        self.recording_thread.start()
        return True

    def stop_recording(self):
        """Detiene la grabación y procesa el audio"""
        self.logger.info("Deteniendo grabación...")
        self.is_recording = False
        if hasattr(self, 'recording_thread'):
            self.recording_thread.join()
        
        frames = []
        while not self.audio_queue.empty():
            frames.append(self.audio_queue.get())
        
        if not frames:
            self.logger.warning("No se capturaron frames de audio")
            return "No se capturó audio"
        
        self.logger.info(f"Frames capturados: {len(frames)}")
        audio_data = np.concatenate(frames)
        audio_file = self.save_audio(audio_data)
        
        if audio_file:
            return self.transcribe_audio(audio_file)
        return "Error al guardar el audio"
    

app = Flask(__name__)
processor = AudioProcessor()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Grabador de Audio</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f0f2f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .button {
            padding: 15px 30px;
            font-size: 18px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 10px;
            outline: none;
        }
        .record {
            background-color: #ff4444;
            color: white;
        }
        .record:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        .record.active {
            background-color: #cc0000;
            animation: pulse 1.5s infinite;
        }
        .transcript {
            margin-top: 20px;
            padding: 20px;
            border-radius: 5px;
            background-color: #f8f9fa;
            min-height: 100px;
            max-height: 400px;
            overflow-y: auto;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .status {
            margin-top: 10px;
            color: #666;
        }
        .device-selector {
            margin-bottom: 20px;
            padding: 10px;
            width: 100%;
            max-width: 400px;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        .error {
            color: #ff4444;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Grabador de Audio a Texto</h1>
        
        <select id="deviceSelector" class="device-selector">
            <option value="">Selecciona un micrófono...</option>
        </select>
        
        <div>
            <button id="recordButton" class="button record" disabled>Iniciar Grabación</button>
        </div>
        
        <div class="status" id="status">Estado: Selecciona un micrófono</div>
        <div class="transcript" id="transcript"></div>
    </div>

    <script>
        const deviceSelector = document.getElementById('deviceSelector');
        const recordButton = document.getElementById('recordButton');
        const statusDiv = document.getElementById('status');
        const transcriptDiv = document.getElementById('transcript');
        let isRecording = false;

        // Cargar dispositivos al iniciar
        fetch('/devices')
            .then(response => response.json())
            .then(devices => {
                devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.id;
                    option.textContent = device.name;
                    deviceSelector.appendChild(option);
                });
            });

        // Manejar cambio de dispositivo
        deviceSelector.addEventListener('change', async () => {
            if (deviceSelector.value) {
                const response = await fetch('/set_device', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ device_id: parseInt(deviceSelector.value) })
                });
                const data = await response.json();
                if (data.success) {
                    recordButton.disabled = false;
                    statusDiv.textContent = 'Estado: Listo para grabar';
                } else {
                    statusDiv.textContent = 'Estado: Error al configurar micrófono';
                }
            } else {
                recordButton.disabled = true;
                statusDiv.textContent = 'Estado: Selecciona un micrófono';
            }
        });

        // Manejar grabación
        recordButton.addEventListener('click', async () => {
            if (!isRecording) {
                const response = await fetch('/start', {method: 'POST'});
                const data = await response.json();
                if (data.success) {
                    isRecording = true;
                    recordButton.textContent = 'Detener Grabación';
                    recordButton.classList.add('active');
                    statusDiv.textContent = 'Estado: Grabando...';
                    deviceSelector.disabled = true;
                }
            } else {
                const response = await fetch('/stop', {method: 'POST'});
                const data = await response.json();
                isRecording = false;
                recordButton.textContent = 'Iniciar Grabación';
                recordButton.classList.remove('active');
                statusDiv.textContent = 'Estado: Listo';
                deviceSelector.disabled = false;
                
                if (data.transcription) {
                    const timestamp = new Date().toLocaleTimeString();
                    const transcriptText = `[${timestamp}] ${data.transcription}`;
                    const newTranscript = document.createElement('p');
                    newTranscript.textContent = transcriptText;
                    transcriptDiv.insertBefore(newTranscript, transcriptDiv.firstChild);
                }
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/devices')
def get_devices():
    return jsonify(processor.get_input_devices())

@app.route('/set_device', methods=['POST'])
def set_device():
    data = request.json
    success = processor.set_input_device(data['device_id'])
    return jsonify({"success": success})

@app.route('/start', methods=['POST'])
def start_recording():
    success = processor.start_recording()
    return jsonify({"success": success, "status": "Recording started" if success else "Failed to start recording"})

@app.route('/stop', methods=['POST'])
def stop_recording():
    text = processor.stop_recording()
    return jsonify({
        "status": "Recording stopped",
        "transcription": text
    })

def open_browser():
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    Timer(0.00000025, open_browser).start()
    app.run(port=5000, debug=False)