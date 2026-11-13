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
        # GROQ_BASE_URL incluye "/openai/v1" porque lo usa CrewAI para el agente. El SDK de
        # Groq lee esa misma variable y le agrega "/openai/v1/..." por su cuenta, lo que
        # duplicaba el prefijo y daba 404. Se quita el sufijo para compartir una sola variable.
        base = os.getenv("GROQ_BASE_URL", "https://api.groq.com")
        base = base.rstrip("/").removesuffix("/openai/v1")
        _client = Groq(api_key=api_key, base_url=base)

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