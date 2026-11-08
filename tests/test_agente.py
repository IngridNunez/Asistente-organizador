import pytest

from src.agente import confirmacion
from src.agente.agente import responder


# Cada test parte sin propuestas y con un calendario que no hace nada real
@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    confirmacion._PENDIENTES.clear()
    monkeypatch.setattr(
        confirmacion.calendario, "crear_evento_calendario", lambda t, i, f: "creado"
    )


def proponer():
    confirmacion.proponer(
        "u1", "Reunión", "2026-11-10T17:00:00", "2026-11-10T18:00:00"
    )


# Un sí con propuesta pendiente lo resuelve el código antes de importar crewai o llamar al LLM
def test_si_ejecuta_la_propuesta_sin_llamar_al_modelo():
    proponer()
    respuesta = responder("sí", "u1")
    assert respuesta.texto == "creado"
    assert respuesta.confirmacion_pendiente is None
    assert confirmacion.pendiente_id("u1") is None


def test_texto_vacio_no_consume_la_propuesta():
    proponer()
    assert responder("   ", "u1").texto == "No te escuché bien. ¿Me lo repites?"
    assert confirmacion.pendiente_id("u1") is not None
