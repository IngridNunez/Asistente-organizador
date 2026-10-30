import base64

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


# Smoke test: confirma que el endpoint responde 200 y trae el campo esperado,
# usando los stubs (no valida contenido real de transcripción/respuesta/voz).
def test_conversar():
    audio = base64.b64encode(b"audio falso").decode()
    respuesta = client.post(
        "/conversar", json={"audio_base64": audio, "usuario_id": "u1"}
    )
    assert respuesta.status_code == 200
    assert "texto_respuesta" in respuesta.json()
