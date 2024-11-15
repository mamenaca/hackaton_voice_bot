from TTS.api import TTS
import torch
from playsound import playsound
import os

# Verificar si CUDA está disponible
gpu_available = torch.cuda.is_available()

# Inicialización del modelo TTS
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True, gpu=gpu_available)

# Función para generar y reproducir audio
def generar_audio(texto, speaker_wav_path, output_path="output_clonacion.wav"):
    # Verificar si el archivo de audio de muestra existe
    if not os.path.exists(speaker_wav_path):
        print(f"El archivo de voz de muestra '{speaker_wav_path}' no existe.")
        return

    # Generar el audio y guardar en un archivo
    tts.tts_to_file(
        text=texto,
        speaker_wav=speaker_wav_path,  # Archivo de voz para clonar
        language="es",  # Idioma español
        file_path=output_path,  # Archivo de salida
        split_sentences=True  # Divide oraciones para mejorar la generación
    )
    print(f"Audio generado en {output_path}")
    # Reproducir el audio generado
    playsound(output_path)

# Ruta al archivo de audio de muestra (asegúrate de que sea un archivo .wav válido)
speaker_wav_path = "Grabación (10).wav"

# Texto a convertir en audio
texto = (
    "Hola, buenas tardes. Estamos haciendo una prueba de sonido para intentar calibrar la voz "
    "de un modelo de inteligencia artificial que responda al servicio al cliente con una voz humana. "
    "En este momento estamos haciendo la calibración con Magic Voice, Magic Mic, y por eso se está "
    "grabando este audio. En este sentido, se está intentando clonar la voz de la persona que está "
    "hablando para poder responder de la manera más natural. Esperamos que el modelo dé un buen resultado "
    "para luego poder utilizar este mismo ejecutable hacia Python y poder solucionar el problema de la "
    "Hackathon. Ya casi se completa un minuto de diálogo. Estoy esperando que se complete el minuto para "
    "terminar la grabación y proceder a cargar el archivo en la aplicación que va a clonar mi voz. Se acaba "
    "de terminar."
)

# Generar y reproducir el audio
generar_audio(texto, speaker_wav_path)
