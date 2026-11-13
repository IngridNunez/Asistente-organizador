import base64
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.api.main import MAX_AUDIO_BASE64, app

client = TestClient(app)

TOKEN = "token-de-prueba"
AUDIO = base64.b64encode(b"audio falso").decode()
CUERPO = {"audio_base64": AUDIO, "usuario_id": "u1"}
CABECERA = {"Authorization": f"Bearer {TOKEN}"}


# Cada test parte con un token configurado y sin el modo "auth desactivada"
@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("API_USUARIO", "u1")
    monkeypatch.delenv("API_AUTH_DISABLED", raising=False)


# Smoke test: confirma que el endpoint responde 200 y trae el campo esperado,
# usando los stubs (no valida contenido real de transcripción/respuesta/voz).
def test_conversar():
    respuesta = client.post("/conversar", json=CUERPO, headers=CABECERA)
    assert respuesta.status_code == 200
    assert "texto_respuesta" in respuesta.json()


def test_sin_token_configurado_falla_cerrado(monkeypatch):
    """Sin `API_AUTH_TOKEN` la API responde 503 aunque llegue un token."""
    monkeypatch.delenv("API_AUTH_TOKEN")
    respuesta = client.post("/conversar", json=CUERPO, headers=CABECERA)
    assert respuesta.status_code == 503


def test_token_incorrecto_o_ausente():
    mal = client.post(
        "/conversar", json=CUERPO, headers={"Authorization": "Bearer otro"}
    )
    assert mal.status_code == 401
    sin = client.post("/conversar", json=CUERPO)
    assert sin.status_code == 401


def test_auth_desactivada_solo_con_bandera_explicita(monkeypatch):
    """Con `API_AUTH_DISABLED=true` se atiende sin token; sin la bandera no."""
    monkeypatch.delenv("API_AUTH_TOKEN")
    monkeypatch.setenv("API_AUTH_DISABLED", "true")
    respuesta = client.post("/conversar", json=CUERPO)
    assert respuesta.status_code == 200


def test_base64_invalido():
    cuerpo = {**CUERPO, "audio_base64": "esto no es base64!!"}
    respuesta = client.post("/conversar", json=cuerpo, headers=CABECERA)
    assert respuesta.status_code == 400


def test_base64_con_saltos_de_linea():
    # encodebytes inserta "\n" cada 76 caracteres, como Android con Base64.DEFAULT
    largo = base64.encodebytes(b"x" * 200).decode()
    cuerpo = {**CUERPO, "audio_base64": largo}
    respuesta = client.post("/conversar", json=cuerpo, headers=CABECERA)
    assert respuesta.status_code == 200


def test_sin_token_gana_sobre_un_body_invalido():
    cuerpo = {**CUERPO, "usuario_id": "../x"}
    assert client.post("/conversar", json=cuerpo).status_code == 401


def test_audio_demasiado_grande():
    cuerpo = {**CUERPO, "audio_base64": "A" * (MAX_AUDIO_BASE64 + 1)}
    respuesta = client.post("/conversar", json=cuerpo, headers=CABECERA)
    assert respuesta.status_code == 422


def test_usuario_sale_de_api_usuario_no_del_body(monkeypatch):
    """El `usuario_id` que llega al agente es `API_USUARIO`; el del body se ignora."""
    usados = []
    monkeypatch.setattr("src.api.main.transcribir", lambda audio: "hola")
    monkeypatch.setattr(
        "src.api.main.responder",
        lambda texto, usuario: usados.append(usuario) or SimpleNamespace(texto="ok"),
    )
    cuerpo = {**CUERPO, "usuario_id": "otro"}
    assert client.post("/conversar", json=cuerpo, headers=CABECERA).status_code == 200
    assert usados == ["u1"]


def test_sin_api_usuario_falla_cerrado(monkeypatch):
    """Con token válido pero sin `API_USUARIO` la API responde 503."""
    monkeypatch.delenv("API_USUARIO")
    assert client.post("/conversar", json=CUERPO, headers=CABECERA).status_code == 503
