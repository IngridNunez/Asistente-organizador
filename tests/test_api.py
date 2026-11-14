import base64
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

# RespuestaAgente: tipo que devuelve el agente, para construir una respuesta simulada.
# api_main: el módulo, para poder reemplazar sus funciones con monkeypatch.
from src.agente.agente import RespuestaAgente
from src.api import main as api_main
from src.api.main import MAX_AUDIO_BASE64, app

client = TestClient(app)

TOKEN = "token-de-prueba"
# No es audio real: el STT está reemplazado en la fixture, así que su contenido no se lee.
AUDIO = base64.b64encode(b"audio falso").decode()
CUERPO = {"audio_base64": AUDIO, "usuario_id": "u1"}
CABECERA = {"Authorization": f"Bearer {TOKEN}"}


# Cada test parte con un token configurado y sin el modo "auth desactivada".
# Además se reemplazan el STT y el agente por versiones locales: estos tests prueban
# la API (auth, validación, encadenado), no a Groq, así que no deben tocar la red
# ni necesitar GROQ_API_KEY.
@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("API_USUARIO", "u1")
    monkeypatch.delenv("API_AUTH_DISABLED", raising=False)
    # Se reemplaza el nombre tal como lo importa main.py ("src.api.main.transcribir"),
    # no el del módulo de voz: es lo que realmente llama el endpoint.
    # STT simulado: devuelve siempre el mismo texto, sin llamar a Whisper.
    monkeypatch.setattr(api_main, "transcribir", lambda audio: "texto de prueba")
    # Agente simulado: repite lo que recibe, así se ve si el texto del STT llegó al agente.
    monkeypatch.setattr(
        api_main,
        "responder",
        lambda texto, usuario_id: RespuestaAgente(texto=f"eco: {texto}"),
    )
    # hablar no se reemplaza: main.py usa hablar_falso, que ya es un stub sin red.


# Comprueba que el endpoint encadena transcribir -> responder -> hablar:
# el texto transcrito llega al agente y su respuesta vuelve en el JSON.
def test_conversar():
    respuesta = client.post("/conversar", json=CUERPO, headers=CABECERA)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["texto_respuesta"] == "eco: texto de prueba"
    assert "audio_base64" in cuerpo


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
