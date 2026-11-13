import base64
import binascii
import hmac
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

# Hoy se importan las versiones "_falso": cada grupo las reemplaza por las
# reales a medida que termina, sin tocar este archivo más que el import.
from src.agente.agente import responder
from src.voz.stt import transcribir
from src.voz.tts import hablar_falso

app = FastAPI()

# ~7,5 MB de audio. Acota el costo de decodificar, transcribir y razonar por petición.
MAX_AUDIO_BASE64 = 10_000_000


# Esquema del body que espera POST /conversar
class ConversarRequest(BaseModel):
    audio_base64: str = Field(max_length=MAX_AUDIO_BASE64)
    # usuario_id será la clave de la memoria del agente: formato acotado
    usuario_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.@-]+$")


# Esquema de la respuesta de POST /conversar
class ConversarResponse(BaseModel):
    texto_respuesta: str
    audio_base64: str


# Exige "Authorization: Bearer <API_AUTH_TOKEN>". Falla cerrado: sin token configurado
# no se atiende a nadie, salvo API_AUTH_DISABLED=true (solo desarrollo local).
def _verificar_token(authorization: str = Header(default="")) -> None:
    if os.getenv("API_AUTH_DISABLED", "").lower() in ("1", "true", "yes"):
        return
    token_esperado = os.getenv("API_AUTH_TOKEN")
    if not token_esperado:
        raise HTTPException(status_code=503, detail="Autenticación no configurada")
    # compare_digest evita filtrar el token por tiempos de respuesta
    if not hmac.compare_digest(
        authorization.encode(), f"Bearer {token_esperado}".encode()
    ):
        raise HTTPException(status_code=401, detail="No autorizado")


# Endpoint principal: recibe audio, devuelve texto y audio de respuesta.
# La dependencia del token corre antes de validar el body: sin token válido siempre es 401/503.
@app.post(
    "/conversar",
    response_model=ConversarResponse,
    dependencies=[Depends(_verificar_token)],
)
def conversar(req: ConversarRequest):
    # audio llega en base64 (JSON no soporta bytes crudos). Se quitan espacios y saltos de línea:
    # Android con Base64.DEFAULT inserta "\n" cada 76 caracteres.
    try:
        audio = base64.b64decode("".join(req.audio_base64.split()), validate=True)
    except binascii.Error:
        raise HTTPException(status_code=400, detail="audio_base64 inválido")

    # Pipeline: voz -> texto -> respuesta del agente -> voz
    texto = transcribir(audio)
    texto_respuesta = responder(texto, req.usuario_id).texto
    audio_respuesta = hablar_falso(texto_respuesta)

    return ConversarResponse(
        texto_respuesta=texto_respuesta,
        audio_base64=base64.b64encode(audio_respuesta).decode(),
    )
