# Texto a voz real: pendiente (la implementa el Grupo Voz con edge-tts o Piper)
def hablar(texto: str) -> bytes:
    raise NotImplementedError


# Stub: no genera audio real, devuelve bytes vacíos para no romper el pipeline
def hablar_falso(texto: str) -> bytes:
    return b""
