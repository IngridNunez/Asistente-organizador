"""Fase 5: presupuesto de herramientas por turno, reintentos y métricas. Sin Groq ni Google reales.

El reintento y la espera se simulan: no hay `sleep` real ni llamadas de red.
"""

import logging

import pytest

from src.agente import agente, confirmacion
from src.agente import tools as tools_mod

SECRETO_USUARIO = "DATO-PERSONAL-FICTICIO-987"
TITULO_OK = "Reunión"
INICIO = "2026-11-10T17:00:00"
FIN = "2026-11-10T18:00:00"
INI2 = "2026-11-10T19:00:00"
FIN2 = "2026-11-10T20:00:00"


class ErrorHTTP(Exception):
    """Error con código HTTP, como los de los SDK de openai y groq: la clasificación mira `status_code`."""

    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.status_code = codigo


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    confirmacion._PENDIENTES.clear()
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("GROQ_BASE_URL", "http://localhost:9")
    monkeypatch.setattr("src.agente.agente.time.sleep", lambda s: None)
    monkeypatch.setattr(confirmacion.calendario, "listar_eventos", lambda d, h: [])
    creados = []
    monkeypatch.setattr(
        confirmacion.calendario,
        "crear_evento_calendario",
        lambda t, i, f: creados.append((t, i, f)) or "creado",
    )
    return creados


@pytest.fixture
def herramientas(monkeypatch):
    """Guarda las tools que construye cada turno, para que el fake del modelo las llame."""
    capturadas = []
    original = tools_mod.construir_tools

    def espia(usuario_id, metricas=None):
        lista = original(usuario_id, metricas)
        capturadas.append(lista)
        return lista

    monkeypatch.setattr(tools_mod, "construir_tools", espia)
    return capturadas


def _fake_kickoff(monkeypatch, guion):
    """Crew.kickoff simulado: ejecuta `guion(tools)` en cada intento; cada intento lanza o devuelve."""
    from crewai import Crew

    intentos = {"n": 0}

    def kickoff(self, *args, **kwargs):
        intentos["n"] += 1
        return guion(intentos["n"], self)

    monkeypatch.setattr(Crew, "kickoff", kickoff)
    return intentos


def _tools_del_turno(herramientas):
    return herramientas[-1]


def test_presupuesto_corta_llamadas_extra_sin_tocar_el_calendario(monkeypatch, herramientas):
    llamadas = []
    monkeypatch.setattr(confirmacion.calendario, "listar_eventos", lambda d, h: llamadas.append(d) or [])

    def guion(n, crew):
        listar = _tools_del_turno(herramientas)[1]
        for _ in range(tools_mod.MAX_LLAMADAS_TURNO + 2):
            resultado = listar.func("2026-11-10T00:00:00", "2026-11-11T00:00:00")
        assert resultado == tools_mod.MENSAJE_PRESUPUESTO
        return "ok"

    _fake_kickoff(monkeypatch, guion)
    agente.responder("mira mi agenda", "u1")
    assert len(llamadas) == tools_mod.MAX_LLAMADAS_TURNO


def test_presupuesto_se_conserva_durante_reintentos(monkeypatch, herramientas, caplog):
    caplog.set_level(logging.INFO)

    def guion(n, crew):
        listar = _tools_del_turno(herramientas)[1]
        for _ in range(4):
            listar.func("2026-11-10T00:00:00", "2026-11-11T00:00:00")
        if n == 1:
            raise ErrorHTTP(429, "429 Too Many Requests")
        return "ok"

    _fake_kickoff(monkeypatch, guion)
    respuesta = agente.responder("mira mi agenda", "u1")
    assert respuesta.texto == "ok"
    # Ambos intentos comparten el mismo contador: 8 llamadas en total, 6 de ellas ejecutadas.
    assert "crew_executions=2 retry_count=1 tool_calls=8" in caplog.text


def test_reintento_no_duplica_la_propuesta(monkeypatch, herramientas):
    def guion(n, crew):
        listar, proponer = _tools_del_turno(herramientas)[1], _tools_del_turno(herramientas)[0]
        listar.func("2026-11-10T00:00:00", "2026-11-11T00:00:00")
        if n == 1:
            raise ErrorHTTP(429, "429")
        proponer.func(TITULO_OK, INICIO, FIN)
        return "ok"

    _fake_kickoff(monkeypatch, guion)
    agente.responder("agéndame algo", "u1")
    assert confirmacion.pendiente_id("u1") is not None
    assert confirmacion._PENDIENTES["u1"].reemplazo is None


def test_confirmacion_no_llama_al_modelo(monkeypatch, herramientas):
    confirmacion.proponer("u1", TITULO_OK, INICIO, FIN)

    def guion(n, crew):
        raise AssertionError("el modelo no debe ejecutarse al confirmar")

    _fake_kickoff(monkeypatch, guion)
    assert agente.responder("sí", "u1").texto == "creado"


def test_rechazo_no_llama_al_modelo(monkeypatch, herramientas):
    confirmacion.proponer("u1", TITULO_OK, INICIO, FIN)
    _fake_kickoff(monkeypatch, lambda n, crew: (_ for _ in ()).throw(AssertionError("no")))
    assert agente.responder("no", "u1").texto == "Listo, no lo creé."


def test_metricas_sin_contenido_y_sin_estimar_tokens(monkeypatch, herramientas, caplog):
    caplog.set_level(logging.INFO)
    _fake_kickoff(monkeypatch, lambda n, crew: "ok")
    agente.responder(f"hola {SECRETO_USUARIO}", "u1")
    assert "crew_executions=1 retry_count=0 tool_calls=0" in caplog.text
    # CrewAI no devolvió uso (el fake devuelve texto plano): se registra como no disponible
    assert "llm_requests=None input_tokens=None output_tokens=None" in caplog.text
    assert "duration_ms=" in caplog.text
    assert SECRETO_USUARIO not in caplog.text


def test_metricas_de_turno_no_se_mezclan_entre_turnos(monkeypatch, herramientas, caplog):
    caplog.set_level(logging.INFO)

    def guion(n, crew):
        listar = _tools_del_turno(herramientas)[1]
        listar.func("2026-11-10T00:00:00", "2026-11-11T00:00:00")
        return "ok"

    _fake_kickoff(monkeypatch, guion)
    agente.responder("uno", "u1")
    agente.responder("dos", "u1")
    assert caplog.text.count("tool_calls=1") == 2
    assert "tool_calls=2" not in caplog.text
