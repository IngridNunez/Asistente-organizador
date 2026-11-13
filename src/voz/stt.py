import os
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

# El .env vive en la raíz del repo (dos niveles arriba de src/voz/stt.py)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Cliente reutilizado entre llamadas (evita recrearlo en cada request)
_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Falta GROQ_API_KEY en .env")
        _client = Groq(api_key=api_key)
    return _client


# Transcripción real: Whisper vía Groq
def transcribir(audio: bytes) -> str:
    resultado = _get_client().audio.transcriptions.create(
        file=("audio.wav", BytesIO(audio).read(), "audio/wav"),
        model=os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo"),
        language="es",
        temperature=0,
    )
    return resultado.text


# Stub: devuelve siempre el mismo texto, para probar el resto del pipeline sin STT real
def transcribir_falso(audio: bytes) -> str:
    return "texto de prueba"