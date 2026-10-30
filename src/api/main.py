import base64
import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

# Hoy se importan las versiones "_falso": cada grupo las reemplaza por las
# reales a medida que termina, sin tocar este archivo más que el import.
from src.agente.agente import responder_falso
from src.voz.stt import transcribir_falso
from src.voz.tts import hablar_falso

app = FastAPI()


# Esquema del body que espera POST /conversar
class ConversarRequest(BaseModel):
    audio_base64: str
    usuario_id: str


# Esquema de la respuesta de POST /conversar
class ConversarResponse(BaseModel):
    texto_respuesta: str
    audio_base64: str

# Endpoint principal: recibe audio, devuelve texto y audio de respuesta
@app.post("/conversar", response_model=ConversarResponse)
def conversar(req: ConversarRequest, authorization: str = Header(default="")):
    # Si hay API_AUTH_TOKEN configurado, exige "Authorization: Bearer <token>"
    token_esperado = os.getenv("API_AUTH_TOKEN")
    if token_esperado and authorization != f"Bearer {token_esperado}":
        raise HTTPException(status_code=401, detail="No autorizado")

    # audio llega en base64 (JSON no soporta bytes crudos)
    audio = base64.b64decode(req.audio_base64)

    # Pipeline: voz -> texto -> respuesta del agente -> voz
    texto = transcribir_falso(audio)
    texto_respuesta = responder_falso(texto, req.usuario_id)
    audio_respuesta = hablar_falso(texto_respuesta)

    return ConversarResponse(
        texto_respuesta=texto_respuesta,
        audio_base64=base64.b64encode(audio_respuesta).decode(),
    )
