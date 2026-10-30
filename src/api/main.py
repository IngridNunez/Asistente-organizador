import base64
import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from src.agente.agente import responder_falso
from src.voz.stt import transcribir_falso
from src.voz.tts import hablar_falso

app = FastAPI()


class ConversarRequest(BaseModel):
    audio_base64: str
    usuario_id: str


class ConversarResponse(BaseModel):
    texto_respuesta: str
    audio_base64: str


@app.post("/conversar", response_model=ConversarResponse)
def conversar(req: ConversarRequest, authorization: str = Header(default="")):
    token_esperado = os.getenv("API_AUTH_TOKEN")
    if token_esperado and authorization != f"Bearer {token_esperado}":
        raise HTTPException(status_code=401, detail="No autorizado")

    audio = base64.b64decode(req.audio_base64)
    texto = transcribir_falso(audio)
    texto_respuesta = responder_falso(texto, req.usuario_id)
    audio_respuesta = hablar_falso(texto_respuesta)

    return ConversarResponse(
        texto_respuesta=texto_respuesta,
        audio_base64=base64.b64encode(audio_respuesta).decode(),
    )
