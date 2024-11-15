import streamlit as st

# Configure Streamlit page first
st.set_page_config(
    page_title="Audio Recorder with Creative Response",
    layout="wide"
)

import pyaudio
import wave
import numpy as np
import google.generativeai as genai
import queue
import time
import logging
import threading
import os
import torch
import pyperclip
from PIL import Image
from pathlib import Path
from TTS.api import TTS
import torch
import IPython

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración del dispositivo
device = "cuda:0" if torch.cuda.is_available() else "cpu"
# Inicialización de audios de ejemplo y modelo de TTS


class AudioProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Audio settings
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        self.format = pyaudio.paInt16
        self.audio = pyaudio.PyAudio()
        self.selected_device = None
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.frames = []
        self.recording_thread = None

        # Mic test settings
        self.test_duration = 3
        self.volume_threshold = 500
        self.is_testing = False
        self.test_frames = []

        self.api_keys = [
            "AIzaSyBG0LMFQgXmkxlIbx-kvmrFzBgZFMbyR-g",
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
        """Initialize and configure the Gemini AI model"""
        try:
            genai.configure(api_key=self.api_keys[self.api_key_index])
            model = genai.GenerativeModel('gemini-1.5-flash')
            self.logger.info("Gemini API configured successfully")
            return model
        except Exception as e:
            self.logger.error(f"Error configuring Gemini API: {str(e)}")
            return None

    def rotate_api_key(self):
        """Rotate to the next API key in the list"""
        self.api_key_index = (self.api_key_index + 1) % len(self.api_keys)
        self.genai_model = self.setup_genai()
        self.logger.info(f"Rotated to API key index: {self.api_key_index}")

    def get_default_input_device(self):
        """Get the default input device index"""
        try:
            default_device = self.audio.get_default_input_device_info()
            return default_device['index']
        except Exception as e:
            self.logger.error(f"Error getting default device: {str(e)}")
            return None

    def test_microphone(self, device_id):
        """Test microphone input and return audio level"""
        if self.is_testing:
            return False
        
        self.is_testing = True
        self.test_frames = []
        max_amplitude = 0
        
        try:
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_id,
                frames_per_buffer=self.chunk_size
            )
            
            start_time = time.time()
            while time.time() - start_time < self.test_duration:
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    self.test_frames.append(data)
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    current_max = np.max(np.abs(audio_data))
                    max_amplitude = max(max_amplitude, current_max)
                except Exception as e:
                    self.logger.error(f"Error reading test audio: {str(e)}")
                    break
            
            stream.stop_stream()
            stream.close()
            
            return max_amplitude > self.volume_threshold
            
        except Exception as e:
            self.logger.error(f"Error testing microphone: {str(e)}")
            return False
        finally:
            self.is_testing = False

    def get_input_devices(self):
        """Get all available input devices with additional info"""
        devices = []
        try:
            default_device_index = self.get_default_input_device()
            
            for i in range(self.audio.get_device_count()):
                device_info = self.audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    devices.append({
                        'id': i,
                        'name': device_info['name'],
                        'channels': device_info['maxInputChannels'],
                        'default_samplerate': device_info['defaultSampleRate'],
                        'is_default': i == default_device_index,
                        'latency': device_info['defaultLowInputLatency']
                    })
        except Exception as e:
            self.logger.error(f"Error getting input devices: {str(e)}")
        return devices

    def verify_device(self, device_id):
        """Verify if the device is working properly"""
        try:
            device_info = self.audio.get_device_info_by_index(device_id)
            
            if (device_info['maxInputChannels'] >= self.channels and
                device_info['defaultSampleRate'] >= self.sample_rate):
                
                test_result = self.test_microphone(device_id)
                return test_result
            
            return False
        except Exception as e:
            self.logger.error(f"Error verifying device: {str(e)}")
            return False

    def set_input_device(self, device_id):
        """Set and verify input device"""
        try:
            if self.verify_device(device_id):
                device_info = self.audio.get_device_info_by_index(device_id)
                self.selected_device = device_id
                self.logger.info(f"Device configured and verified: {device_info['name']}")
                return True
            else:
                self.logger.error("Device verification failed")
                return False
        except Exception as e:
            self.logger.error(f"Error setting input device: {str(e)}")
            return False

    def start_recording(self):
        """Start audio recording"""
        if self.selected_device is None:
            self.logger.error("No input device selected")
            return False
        
        if self.is_recording:
            self.logger.warning("Already recording")
            return False
        
        self.is_recording = True
        self.frames = []
        
        def record_audio():
            try:
                stream = self.audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=self.selected_device,
                    frames_per_buffer=self.chunk_size
                )
                
                self.logger.info("Recording started")
                while self.is_recording:
                    try:
                        data = stream.read(self.chunk_size, exception_on_overflow=False)
                        self.frames.append(data)
                    except Exception as e:
                        self.logger.error(f"Error reading audio data: {str(e)}")
                        break
                
                stream.stop_stream()
                stream.close()
                self.logger.info("Recording stopped")
                
            except Exception as e:
                self.logger.error(f"Error in recording: {str(e)}")
                self.is_recording = False
        
        self.recording_thread = threading.Thread(target=record_audio)
        self.recording_thread.start()
        return True

    def stop_recording(self):
        """Stop audio recording and save the file"""
        if not self.is_recording:
            return "No active recording"
        
        self.logger.info("Stopping recording...")
        self.is_recording = False
        
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join()
        
        if not self.frames:
            self.logger.warning("No audio frames captured")
            return "No audio captured"
        
        try:
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            filename = temp_dir / "temp_audio.wav"
            
            with wave.open(str(filename), 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.frames))
            
            return self.transcribe_audio(str(filename))
        except Exception as e:
            self.logger.error(f"Error saving audio: {str(e)}")
            return "Error saving audio recording"

    def transcribe_audio(self, audio_file):
        """Transcribe the recorded audio using Gemini AI"""
        try:
            if not os.path.exists(audio_file):
                self.logger.error(f"Audio file does not exist: {audio_file}")
                return None

            audio_file = genai.upload_file(path=audio_file)
            prompt = ["Transcribe el siguiente audio en español:", audio_file]
            
            response = self.genai_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=2000,
                    temperature=0.2,
                    top_p=0.8,
                    top_k=40
                )
            )
            output="LOTR.wav"
            texto=response.text
            SAMPLE_AUDIOS = ["Grabación-_10_.mp3"]  # Usar solo un archivo de ejemplo o ajustar lista según necesidades
            tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False).to(device)
            tts.tts_to_file(
            texto,
            speaker_wav=SAMPLE_AUDIOS,  # Solo carga los audios de ejemplo una vez
            language="es",
            file_path=output,
            split_sentences=True
        )
            audio = IPython.display.Audio(output)
            display(audio)


            
        except Exception as e:
            self.logger.error(f"Transcription error: {str(e)}")
            self.rotate_api_key()
            return f"Transcription error: {str(e)}"

    def __del__(self):
        if hasattr(self, 'audio'):
            self.audio.terminate()

def initialize_session_state():
    """Initialize the session state variables"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.processor = AudioProcessor()
        st.session_state.recording = False
        st.session_state.device_configured = False
        st.session_state.transcription_history = []
        st.session_state.mic_test_status = None

def render_sidebar():
    """Render the sidebar content"""
    st.sidebar.header("Microphone Configuration")
    
    devices = st.session_state.processor.get_input_devices()
    if not devices:
        st.sidebar.error("No input devices found")
        return
    
    default_device_index = next(
        (i for i, d in enumerate(devices) if d['is_default']), 0
    )
    
    st.sidebar.subheader("Available Microphones")
    device_index = st.sidebar.selectbox(
        "Select a microphone",
        range(len(devices)),
        format_func=lambda x: f"{devices[x]['name']} {'(Default)' if devices[x]['is_default'] else ''}",
        index=default_device_index
    )
    
    selected_device = devices[device_index]
    st.sidebar.write("Device Details:")
    st.sidebar.write(f"- Channels: {selected_device['channels']}")
    st.sidebar.write(f"- Sample Rate: {selected_device['default_samplerate']:.0f} Hz")
    st.sidebar.write(f"- Latency: {selected_device['latency']*1000:.1f} ms")

    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("Test Microphone"):
            with st.spinner("Testing microphone..."):
                test_result = st.session_state.processor.test_microphone(selected_device['id'])
                if test_result:
                    st.session_state.mic_test_status = "success"
                    st.success("Microphone test successful!")
                else:
                    st.session_state.mic_test_status = "error"
                    st.error("Microphone test failed. Please check your settings.")

    with col2:
        if st.button("Configure Microphone"):
            with st.spinner("Configuring microphone..."):
                if st.session_state.processor.set_input_device(selected_device['id']):
                    st.session_state.device_configured = True
                    st.success(f"Microphone configured successfully")
                else:
                    st.error("Error configuring microphone")

def render_main_content():
    """Render the main content area"""
    col1, col2 = st.columns([1, 2])

    with col1:
        st.write("Status:", "Recording" if st.session_state.recording else "Stopped")
        
        if not st.session_state.device_configured:
            st.warning("Please configure a microphone first")
        elif not st.session_state.recording:
            if st.button("📝 Start Recording"):
                if st.session_state.processor.start_recording():
                    st.session_state.recording = True
                    st.rerun()
        else:
            if st.button("⏹️ Stop Recording", type="primary"):
                transcription = st.session_state.processor.stop_recording()
                st.session_state.recording = False
                
                if transcription and transcription != "No audio captured":
                    st.session_state.transcription_history.insert(0, {
                        'timestamp': time.strftime('%H:%M:%S'),
                        'transcription': transcription,
                        'audio_status': "✅"
                    })
                st.rerun()

    with col2:
        st.subheader("Transcription History")
        if not st.session_state.transcription_history:
            st.info("No transcriptions yet. Start recording to see your history here.")
        else:
            for entry in st.session_state.transcription_history:
                with st.expander(f"[{entry['timestamp']}] {entry['audio_status']}"):
                    st.write("📝 Transcription:")
                    st.write(entry['transcription'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗑️ Delete", key=f"delete_{entry['timestamp']}"):
                            st.session_state.transcription_history.remove(entry)
                            st.rerun()
                    with col2:
                        if st.button("📋 Copy", key=f"copy_{entry['timestamp']}"):
                            pyperclip.copy(entry['transcription'])
                            st.toast("Copied to clipboard!")

def render_footer():
    """Render the footer content"""
    st.markdown("---")
    
    # About section
    with st.expander("ℹ️ About"):
        st.markdown("""
        ### Audio Recorder with Creative Response
        
        This application allows you to:
        - Record audio from your microphone
        - Transcribe the audio to text using Gemini AI
        - View and manage your transcription history
        
        **Tips:**
        - Make sure to configure and test your microphone before recording
        - Speak clearly for better transcription results
        - You can copy or delete transcriptions from the history
        """)
    
    # Settings section
    with st.expander("⚙️ Settings"):
        st.subheader("Audio Settings")
        st.write(f"Sample Rate: {st.session_state.processor.sample_rate} Hz")
        st.write(f"Channels: {st.session_state.processor.channels}")
        st.write(f"Chunk Size: {st.session_state.processor.chunk_size}")
        
        new_threshold = st.slider(
            "Microphone Sensitivity",
            min_value=100,
            max_value=1000,
            value=st.session_state.processor.volume_threshold,
            step=50
        )
        if new_threshold != st.session_state.processor.volume_threshold:
            st.session_state.processor.volume_threshold = new_threshold
            st.success("Sensitivity updated!")

    # Credits
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
            <p>Developed with ❤️ using Streamlit, Gemini API and TTS</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def main():
    # Initialize session state
    initialize_session_state()

    # Set page title
    st.title("Audio Recorder with Creative Response")

    # Render sidebar
    render_sidebar()

    # Render main content
    render_main_content()

    # Render footer
    render_footer()

if __name__ == "__main__":
    main()
