import sounddevice as sd
import numpy as np
import wave
import google.generativeai as genai
import base64
import threading
import queue
import time
import logging
import os

class ProcesadorAudio:
    def __init__(self):
        # Inicializamos el logger
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Ajustes de audio mejorados
        self.frecuencia_muestreo = 16000  # Antes sample_rate
        self.canales = 1         # Antes channels
        self.tamano_chunk = 1024    # Antes chunk_size
        self.tipo_datos = np.int16     # Antes dtype
        self.dispositivo_seleccionado = None  # Antes selected_device
        
        # Inicializamos el resto de atributos
        self.api_keys = [
            "AIzaSyBhnvqxLjhzfbUp3MnFjwEMsNJ4VYY7r3A",
            "AIzaSyB5wvYrrT1DzA4bH4oRLuO0lF4TS3fMiw8",
            "AIzaSyDKj4QW99q9Kfvues0AtSmGRGNqhYrUr7A",
            "AIzaSyCIt5-vZ45sYP-VlEF98fFbpZAbWOmdNz0",
            "AIzaSyDKzJgxKgHo8mOZ7pJueCRW57x0OQYObBY",
            "AIzaSyD9Bu2jX6jXbuuaTW2Sjh4hhUeuJdYD23s"
        ]
        self.indice_api = 0  # Antes api_key_index
        self.cola_audio = queue.Queue()  # Antes audio_queue
        self.grabando = False  # Antes is_recording
        
        # Configuramos Gemini
        self.modelo_genai = self.configurar_genai()  # Antes genai_model
        
    def configurar_genai(self):  # Antes setup_genai
        try:
            genai.configure(api_key=self.api_keys[self.indice_api])
            modelo = genai.GenerativeModel('gemini-1.5-flash')
            self.logger.info("Gemini API configurada exitosamente")
            return modelo
        except Exception as e:
            self.logger.error(f"Error configurando Gemini API: {str(e)}")
            return None

    def rotar_api_key(self):  # Antes rotate_api_key
        self.indice_api = (self.indice_api + 1) % len(self.api_keys)
        self.modelo_genai = self.configurar_genai()
        self.logger.info(f"API key rotada al índice: {self.indice_api}")

    def obtener_dispositivos_entrada(self):  # Antes get_input_devices
        dispositivos = sd.query_devices()
        dispositivos_entrada = []
        for i, dispositivo in enumerate(dispositivos):
            if dispositivo['max_input_channels'] > 0:
                dispositivos_entrada.append({
                    'id': i,
                    'nombre': dispositivo['name'],
                    'canales': dispositivo['max_input_channels'],
                    'frecuencia_muestreo': dispositivo['default_samplerate']
                })
        return dispositivos_entrada

    def configurar_dispositivo_entrada(self, id_dispositivo):  # Antes set_input_device
        try:
            info_dispositivo = sd.query_devices(id_dispositivo, 'input')
            self.dispositivo_seleccionado = id_dispositivo
            
            frecuencia_sugerida = int(info_dispositivo['default_samplerate'])
            if 16000 <= frecuencia_sugerida <= 48000:
                self.frecuencia_muestreo = frecuencia_sugerida
            else:
                self.frecuencia_muestreo = 16000
                
            self.canales = 1
            self.logger.info(f"Dispositivo configurado: {info_dispositivo['name']} @ {self.frecuencia_muestreo}Hz")
            return True
        except Exception as e:
            self.logger.error(f"Error configurando dispositivo: {str(e)}")
            return False

    def callback_audio(self, indata, frames, time, status):  # Antes audio_callback
        if status:
            self.logger.warning(f"Estado del callback de audio: {status}")
        self.cola_audio.put(indata.copy())
        self.logger.debug(f"Audio recibido: {indata.shape} frames")

    def guardar_audio(self, frames, nombre_archivo="temp_audio.wav"):  # Antes save_audio
        try:
            with wave.open(nombre_archivo, 'wb') as wf:
                wf.setnchannels(self.canales)
                wf.setsampwidth(2)
                wf.setframerate(self.frecuencia_muestreo)
                wf.writeframes(frames.tobytes())
            
            tamano_archivo = os.path.getsize(nombre_archivo)
            self.logger.info(f"Archivo de audio guardado: {nombre_archivo} ({tamano_archivo} bytes)")
            return nombre_archivo
        except Exception as e:
            self.logger.error(f"Error guardando audio: {str(e)}")
            return None

    def transcribir_audio(self, archivo_audio):  # Antes transcribe_audio
        try:
            if not os.path.exists(archivo_audio):
                self.logger.error(f"El archivo de audio no existe: {archivo_audio}")
                return None

            with open(archivo_audio, 'rb') as f:
                bytes_audio = f.read()
            
            self.logger.info(f"Tamaño del audio en bytes: {len(bytes_audio)}")
            archivo_audio = genai.upload_file(path=archivo_audio)
            prompt = ["Transcribe el siguiente audio en español:", archivo_audio]
            
            respuesta = self.modelo_genai.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=200,
                    temperature=0.2,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            self.logger.info(f"Respuesta recibida de Gemini: {respuesta.text}")
            return respuesta.text
            
        except Exception as e:
            self.logger.error(f"Error en transcripción: {str(e)}")
            self.rotar_api_key()
            return f"Error en transcripción: {str(e)}"

    def iniciar_grabacion(self):  # Antes start_recording
        if self.dispositivo_seleccionado is None:
            self.logger.error("No se ha seleccionado dispositivo de entrada")
            return False
        
        self.logger.info(f"Iniciando grabación con dispositivo {self.dispositivo_seleccionado}...")
        self.grabando = True
        self.cola_audio = queue.Queue()
        
        def grabar_audio():
            try:
                with sd.InputStream(
                    callback=self.callback_audio,
                    device=self.dispositivo_seleccionado,
                    channels=self.canales,
                    samplerate=self.frecuencia_muestreo,
                    dtype=self.tipo_datos,
                    blocksize=self.tamano_chunk,
                    latency='low'
                ):
                    self.logger.info("Stream de audio iniciado")
                    while self.grabando:
                        time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error en grabación: {str(e)}")
        
        self.hilo_grabacion = threading.Thread(target=grabar_audio)
        self.hilo_grabacion.start()
        return True

    def detener_grabacion(self):  # Antes stop_recording
        self.logger.info("Deteniendo grabación...")
        self.grabando = False
        if hasattr(self, 'hilo_grabacion'):
            self.hilo_grabacion.join()
        
        frames = []
        while not self.cola_audio.empty():
            frames.append(self.cola_audio.get())
        
        if not frames:
            self.logger.warning("No se capturaron frames de audio")
            return "No se capturó audio"
        
        self.logger.info(f"Frames capturados: {len(frames)}")
        audio_data = np.concatenate(frames)
        archivo_audio = self.guardar_audio(audio_data)
        
        if archivo_audio:
            return self.transcribir_audio(archivo_audio)
        return "Error al guardar el audio"