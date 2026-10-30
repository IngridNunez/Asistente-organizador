# Razonamiento real: pendiente (lo implementa el Grupo Agente con LangChain + Groq)
# Debería devolver RespuestaAgente (ver docs/contratos.md), no solo str
def responder(texto: str, usuario_id: str) -> str:
    raise NotImplementedError


# Stub: hace eco del texto recibido, sin LLM ni memoria real
def responder_falso(texto: str, usuario_id: str) -> str:
    return f"Recibí: {texto}"
