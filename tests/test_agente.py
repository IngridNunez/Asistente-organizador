import pytest

from src.agente import confirmacion
from src.agente.agente import _crear_llm, responder
from src.agente.tools import construir_tools


# Cada test parte sin propuestas y con un calendario que no hace nada real
@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    confirmacion._PENDIENTES.clear()
    monkeypatch.setattr(
        confirmacion.calendario, "crear_evento_calendario", lambda t, i, f: "creado"
    )


def proponer():
    confirmacion.proponer("u1", "Reunión", "2026-11-10T17:00:00", "2026-11-10T18:00:00")


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


# Si Groq falla a mitad del turno, la propuesta que el usuario nunca vio no debe quedar viva
def test_falla_de_groq_descarta_la_propuesta(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("GROQ_BASE_URL", "http://localhost:9")

    def kickoff_roto(self, *args, **kwargs):
        proponer()  # el modelo alcanzó a proponer antes de caerse
        raise RuntimeError("groq caído")

    monkeypatch.setattr("crewai.Crew.kickoff", kickoff_roto)
    respuesta = responder("agéndame algo mañana", "u1")
    assert respuesta.texto.startswith("Tuve un problema")
    assert confirmacion.pendiente_id("u1") is None


def test_crear_llm_sin_claves_falla_claro(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_BASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        _crear_llm()


def test_tool_proponer_con_fechas_malas_devuelve_error_al_modelo():
    proponer_tool = construir_tools("u1")[0]
    assert proponer_tool.func("Reunión", "mañana", "pasado").startswith("Error:")
    assert confirmacion.pendiente_id("u1") is None


# El modelo debe recibir lo que se guardó, para que el usuario confirme lo que se creará
def test_tool_proponer_devuelve_lo_guardado():
    proponer_tool = construir_tools("u1")[0]
    resultado = proponer_tool.func(
        "Reunión", "2026-11-10T17:00:00", "2026-11-10T18:00:00"
    )
    assert "Reunión" in resultado
    assert "2026-11-10T17:00:00" in resultado
    assert "2026-11-10T18:00:00" in resultado
    assert confirmacion.pendiente_id("u1") is not None


def test_tool_listar_eventos_no_propaga_errores_del_calendario(monkeypatch):
    def roto(desde, hasta):
        raise RuntimeError("token vencido")

    monkeypatch.setattr(confirmacion.calendario, "listar_eventos", roto)
    listar = construir_tools("u1")[1]
    assert listar.func("2026-11-10T00:00:00", "2026-11-11T00:00:00").startswith(
        "Error:"
    )
