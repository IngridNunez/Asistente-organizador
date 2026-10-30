# Transcripción real: pendiente (la implementa el Grupo Voz con Whisper vía Groq)
def transcribir(audio: bytes) -> str:
    raise NotImplementedError


# Stub: devuelve siempre el mismo texto, para probar el resto del pipeline sin STT real
def transcribir_falso(audio: bytes) -> str:
    return "texto de prueba"
