from pydantic import BaseModel


# Respuesta del agente (ver docs/contratos.md)
class RespuestaAgente(BaseModel):
    texto: str  # siempre presente, es lo que se pasa a TTS
    accion_local: dict | None = None  # {"accion": str, "params": dict}, la ejecuta el cliente con allowlist
    confirmacion_pendiente: str | None = None  # id de la acción que espera un sí/no del usuario


# Razonamiento real: pendiente (lo implementa el Grupo Agente con CrewAI + Groq)
def responder(texto: str, usuario_id: str) -> RespuestaAgente:
    raise NotImplementedError


# Stub: hace eco del texto recibido, sin LLM ni memoria real
def responder_falso(texto: str, usuario_id: str) -> RespuestaAgente:
    return RespuestaAgente(texto=f"Recibí: {texto}")
