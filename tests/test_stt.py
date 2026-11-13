from unittest.mock import MagicMock

import pytest

from src.voz import stt


# stt._client es un singleton: cada test parte con uno nuevo para no heredar estado
@pytest.fixture(autouse=True)
def limpiar_cliente():
    stt._client = None


# Cliente de Groq falso: ningún test de transcripción llama a la API real ni gasta la cuota
@pytest.fixture
def cliente(monkeypatch):
    falso = MagicMock()
    falso.audio.transcriptions.create.return_value.text = "hola, esto es una prueba"
    monkeypatch.setattr(stt, "_get_client", lambda: falso)
    return falso


# --- transcribir ------------------------------------------------------------


def test_transcribir_devuelve_el_texto_de_groq(cliente):
    assert stt.transcribir(b"audio") == "hola, esto es una prueba"


def test_transcribir_manda_audio_como_wav(cliente):
    stt.transcribir(b"audio")
    kwargs = cliente.audio.transcriptions.create.call_args.kwargs
    nombre, datos, mime = kwargs["file"]
    assert nombre == "audio.wav"
    assert datos == b"audio"
    assert mime == "audio/wav"


def test_transcribir_usa_el_modelo_del_entorno_y_espanol(cliente, monkeypatch):
    monkeypatch.setenv("GROQ_STT_MODEL", "whisper-large-v3")
    stt.transcribir(b"audio")
    kwargs = cliente.audio.transcriptions.create.call_args.kwargs
    assert kwargs["model"] == "whisper-large-v3"
    assert kwargs["language"] == "es"
    assert kwargs["temperature"] == 0


def test_transcribir_usa_el_modelo_por_defecto_sin_variable(cliente, monkeypatch):
    monkeypatch.delenv("GROQ_STT_MODEL", raising=False)
    stt.transcribir(b"audio")
    kwargs = cliente.audio.transcriptions.create.call_args.kwargs
    assert kwargs["model"] == "whisper-large-v3-turbo"


def test_transcribir_propaga_errores_de_groq(cliente):
    cliente.audio.transcriptions.create.side_effect = RuntimeError("groq caído")
    with pytest.raises(RuntimeError, match="groq caído"):
        stt.transcribir(b"audio")


# --- _get_client ------------------------------------------------------------


def test_sin_api_key_falla_claro(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        stt._get_client()


def test_get_client_reutiliza_la_instancia(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    assert stt._get_client() is stt._get_client()


# --- transcribir_falso ------------------------------------------------------


def test_transcribir_falso_devuelve_texto_fijo():
    assert stt.transcribir_falso(b"cualquier cosa") == "texto de prueba"
