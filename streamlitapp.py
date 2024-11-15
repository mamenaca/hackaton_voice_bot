import sounddevice as sd
import numpy as np
import wave
import google.generativeai as genai
import base64
import queue
import time
import logging
import os
import streamlit as st

class AudioProcessor:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        self.dtype = np.int16
        self.selected_device = None
        self.audio_queue = queue.Queue()
        self.is_recording = False

        self.api_keys = [
            "AIzaSyBhnvqxLjhzfbUp3MnFjwEMsNJ4VYY7r3A",
            "AIzaSyB5wvYrrT1DzA4bH4oRLuO0lF4TS3fMiw8",
            "AIzaSyDKj4QW99q9Kfvues0AtSmGRGNqhYrUr7A",
            "AIzaSyCIt5-vZ45sYP-VlEF98fFbpZAbWOmdNz0",
            "AIzaSyDKzJgxKgHo8mOZ7pJueCRW57x0OQYObBY",
            "AIzaSyD9Bu2jX6jXbuuaTW2Sjh4hhUeuJdYD23s"
        ]
        self.api_key_index = 0
        self.genai_model = self.setup_genai()

    def setup_genai(self):
        try:
            genai.configure(api_key=self.api_keys[self.api_key_index])
            model = genai.GenerativeModel('gemini-1.5-flash')
            self.logger.info("Gemini API configurada exitosamente")
            return model
        except Exception as e:
            self.logger.error(f"Error configurando Gemini API: {str(e)}")
            return None

    def rotate_api_key(self):
        self.api_key_index = (self.api_key_index + 1) % len(self.api_keys)
        self.genai_model = self.setup_genai()
        self.logger.info(f"Rotated to API key index: {self.api_key_index}")

    def get_input_devices(self):
        devices = sd.query_devices()
        input_devices = [
            {"id": i, "name": device['name']}
            for i, device in enumerate(devices)
            if device['max_input_channels'] > 0
        ]
        return input_devices

    def set_input_device(self, device_id):
        try:
            device_info = sd.query_devices(device_id, 'input')
            self.selected_device = device_id
            self.sample_rate = int(device_info['default_samplerate'])
            self.logger.info(f"Dispositivo configurado: {device_info['name']} @ {self.sample_rate}Hz")
            return True
        except Exception as e:
            self.logger.error(f"Error configurando dispositivo: {str(e)}")
            return False

    def audio_callback(self, indata, frames, time, status):
        if status:
            self.logger.warning(f"Audio callback status: {status}")
        self.audio_queue.put(indata.copy())

    def save_audio(self, frames, filename="temp_audio.wav"):
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(frames.tobytes())
            return filename
        except Exception as e:
            self.logger.error(f"Error guardando audio: {str(e)}")
            return None

    def transcribe_audio(self, audio_file):
        try:
            with open(audio_file, 'rb') as f:
                audio_bytes = f.read()

            audio_b64 = base64.b64encode(audio_bytes).decode()
            audio_file = genai.upload_file(path=audio_file)

            prompt = ["Transcribe el siguiente audio en español:", audio_file]
            response = self.genai_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1, max_output_tokens=200, temperature=0.2, top_p=0.8, top_k=40
                )
            )
            return response.text
        except Exception as e:
            self.logger.error(f"Error en transcripción: {str(e)}")
            self.rotate_api_key()
            return f"Error en transcripción: {str(e)}"

    def start_recording(self):
        if self.selected_device is None:
            self.logger.error("No se ha seleccionado dispositivo de entrada")
            return False

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
                    blocksize=self.chunk_size
                ):
                    while self.is_recording:
                        time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error en grabación: {str(e)}")

        self.recording_thread = threading.Thread(target=record_audio)
        self.recording_thread.start()
        return True

    def stop_recording(self):
        self.is_recording = False
        if hasattr(self, 'recording_thread'):
            self.recording_thread.join()

        frames = []
        while not self.audio_queue.empty():
            frames.append(self.audio_queue.get())

        if frames:
            audio_data = np.concatenate(frames)
            audio_file = self.save_audio(audio_data)
            if audio_file:
                return self.transcribe_audio(audio_file)
        return "No se capturó audio"


# Inicializar procesador de audio
processor = AudioProcessor()

# Streamlit UI
st.title("Grabador de Audio a Texto")
st.sidebar.header("Configuración de Dispositivo")

# Seleccionar micrófono
devices = processor.get_input_devices()
device_names = [device['name'] for device in devices]
device_index = st.sidebar.selectbox("Selecciona un micrófono", range(len(device_names)), format_func=lambda x: device_names[x])

if st.sidebar.button("Configurar Micrófono"):
    if processor.set_input_device(devices[device_index]['id']):
        st.sidebar.success(f"Micrófono configurado: {device_names[device_index]}")
    else:
        st.sidebar.error("Error configurando micrófono")

# Botón de grabar
if st.button("Iniciar Grabación"):
    if processor.start_recording():
        st.success("Grabación iniciada")
    else:
        st.error("Error iniciando grabación")

if st.button("Detener Grabación"):
    transcription = processor.stop_recording()
    st.text_area("Transcripción", transcription, height=300)
