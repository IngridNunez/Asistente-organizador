"""Reintentos del turno: limpieza de propuestas del intento fallido y clasificación del 429.

Modelo y calendario simulados. Sin Groq ni Google.
"""

import groq
import httpx
import openai
import pytest
from crewai import Crew

from src.agente import agente, confirmacion
from src.agente import tools as tools_mod

DIA = ("2026-11-10T00:00:00", "2026-11-11T00:00:00")
INI, FIN = "2026-11-10T15:00:00", "2026-11-10T16:00:00"
INI2, FIN2 = "2026-11-10T17:00:00", "2026-11-10T18:00:00"
MENSAJE_ERROR = "Tuve un problema para responder. Intenta de nuevo en un momento."


def _respuesta(codigo):
    """Respuesta HTTP mínima para construir excepciones del SDK."""
    return httpx.Response(codigo, request=httpx.Request("POST", "http://test/v1/chat/completions"))


def limite_openai():
    """Error 429 con la forma del SDK de openai (el mensaje incluye el código)."""
    return openai.RateLimitError(
        "Error code: 429 - rate_limit_exceeded", response=_respuesta(429), body=None
    )


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    """Estado limpio, sin esperas reales y calendario en memoria."""
    confirmacion._PENDIENTES.clear()
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("GROQ_BASE_URL", "http://localhost:9")
    esperas = []
    monkeypatch.setattr("src.agente.agente.time.sleep", esperas.append)
    creados = []
    monkeypatch.setattr(
        confirmacion.calendario,
        "crear_evento_calendario",
        lambda t, i, f: creados.append((t, i, f)) or "creado",
    )
    monkeypatch.setattr(confirmacion.calendario, "listar_eventos", lambda d, h: [])
    return {"creados": creados, "esperas": esperas}


def correr(monkeypatch, guion):
    """Simula `Crew.kickoff`: `guion(intento, proponer, listar)` corre en cada intento del turno.

    Devuelve un dict con el número de intentos ejecutados en la clave `"n"`.
    """
    capturadas = []
    original = tools_mod.construir_tools

    def espia(usuario_id, metricas=None):
        """Guarda las herramientas que construye cada turno."""
        lista = original(usuario_id, metricas)
        capturadas.append(lista)
        return lista

    monkeypatch.setattr(tools_mod, "construir_tools", espia)
    intentos = {"n": 0}

    def kickoff(self, *args, **kwargs):
        """Ejecuta un intento del guion con las herramientas del turno."""
        intentos["n"] += 1
        proponer, listar = capturadas[-1]
        return guion(intentos["n"], proponer, listar)

    monkeypatch.setattr(Crew, "kickoff", kickoff)
    return intentos


# --- Propuestas del intento fallido (R1) ---


def test_propuesta_de_intento_fallido_no_queda_pendiente(monkeypatch, entorno):
    """El intento que falla con 429 no deja una propuesta que el usuario nunca vio."""

    def guion(n, proponer, listar):
        """Primer intento propone y falla; el segundo no propone."""
        listar.func(*DIA)
        if n == 1:
            proponer.func("Reunión", INI, FIN)
            raise limite_openai()
        return "Sin propuesta por ahora."

    correr(monkeypatch, guion)
    respuesta = agente.responder("agéndame una reunión", "u1")
    assert confirmacion.pendiente_id("u1") is None
    assert respuesta.confirmacion_pendiente is None
    assert entorno["creados"] == []


def test_propuesta_del_reintento_no_es_reemplazo(monkeypatch, entorno):
    """La propuesta del intento que sí llega es la propuesta activa, no un reemplazo de la fallida."""

    def guion(n, proponer, listar):
        """Primer intento propone y falla; el segundo propone otra cosa."""
        listar.func(*DIA)
        if n == 1:
            proponer.func("Reunión", INI, FIN)
            raise limite_openai()
        proponer.func("Almuerzo", INI2, FIN2)
        return "ok"

    correr(monkeypatch, guion)
    respuesta = agente.responder("agéndame algo", "u1")
    accion = confirmacion._PENDIENTES["u1"]
    assert accion.titulo == "Almuerzo"
    assert accion.reemplazo is None
    assert respuesta.confirmacion_pendiente == accion.id
    assert entorno["creados"] == []


def test_propuesta_anterior_al_turno_se_conserva(monkeypatch, entorno):
    """Una propuesta vigente antes del turno sigue activa tras un intento fallido."""
    confirmacion.proponer("u1", "Gimnasio", "2026-11-12T19:00:00", "2026-11-12T20:00:00")

    def guion(n, proponer, listar):
        """Primer intento propone y falla; el segundo propone una alternativa."""
        listar.func(*DIA)
        if n == 1:
            proponer.func("Reunión", INI, FIN)
            raise limite_openai()
        proponer.func("Almuerzo", INI2, FIN2)
        return "ok"

    correr(monkeypatch, guion)
    agente.responder("cambia algo", "u1")
    accion = confirmacion._PENDIENTES["u1"]
    assert accion.titulo == "Gimnasio"
    assert accion.reemplazo is not None and accion.reemplazo.titulo == "Almuerzo"
    assert entorno["creados"] == []


def test_reintento_no_ejecuta_el_calendario(monkeypatch, entorno):
    """Ningún intento del turno crea eventos: solo `resolver` puede hacerlo."""

    def guion(n, proponer, listar):
        """Dos intentos con propuesta; el primero falla."""
        listar.func(*DIA)
        proponer.func("Reunión", INI, FIN)
        if n == 1:
            raise limite_openai()
        return "ok"

    correr(monkeypatch, guion)
    agente.responder("agéndame algo", "u1")
    assert entorno["creados"] == []


def test_reintento_no_reinicia_el_presupuesto(monkeypatch, entorno):
    """El presupuesto de llamadas del turno sigue contando entre intentos."""
    resultados = []

    def guion(n, proponer, listar):
        """Primer intento gasta 4 llamadas y falla; el segundo gasta 3 más."""
        if n == 1:
            for _ in range(4):
                listar.func(*DIA)
            raise limite_openai()
        for _ in range(3):
            resultados.append(listar.func(*DIA))
        return "ok"

    correr(monkeypatch, guion)
    agente.responder("mira mi agenda", "u1")
    assert resultados[0] != tools_mod.MENSAJE_PRESUPUESTO
    assert resultados[-1] == tools_mod.MENSAJE_PRESUPUESTO


# --- Clasificación del 429 por código HTTP (R4) ---


def test_429_real_se_reintenta_y_luego_responde(monkeypatch, entorno):
    """Un RateLimitError real se reintenta y la respuesta llega cuando se libera el límite."""

    def guion(n, proponer, listar):
        """Falla la primera vez con 429."""
        if n == 1:
            raise limite_openai()
        return "ok"

    intentos = correr(monkeypatch, guion)
    assert agente.responder("hola", "u1").texto == "ok"
    assert intentos["n"] == 2
    assert entorno["esperas"] == [4]


def test_429_agotado_da_mensaje_sin_traza(monkeypatch, entorno):
    """Si el 429 persiste, se agotan los reintentos y el usuario recibe el mensaje de error."""

    def guion(n, proponer, listar):
        """Siempre falla con 429."""
        raise limite_openai()

    intentos = correr(monkeypatch, guion)
    assert agente.responder("hola", "u1").texto == MENSAJE_ERROR
    assert intentos["n"] == agente.REINTENTOS_RATE_LIMIT + 1
    assert entorno["esperas"] == [4, 8]


def test_rate_limit_de_groq_se_reintenta(monkeypatch, entorno):
    """El RateLimitError del SDK de groq también se reintenta por su código HTTP."""

    def guion(n, proponer, listar):
        """Falla la primera vez con el error del SDK de groq."""
        if n == 1:
            raise groq.RateLimitError("límite", response=_respuesta(429), body=None)
        return "ok"

    intentos = correr(monkeypatch, guion)
    assert agente.responder("hola", "u1").texto == "ok"
    assert intentos["n"] == 2


def test_texto_con_429_sin_codigo_http_no_se_reintenta(monkeypatch, entorno):
    """Un error cuyo texto contiene 429 pero que no trae código HTTP 429 no se reintenta."""

    def guion(n, proponer, listar):
        """Falla con un RuntimeError que menciona 429."""
        raise RuntimeError("Falló con el código 429 del proveedor")

    intentos = correr(monkeypatch, guion)
    assert agente.responder("hola", "u1").texto == MENSAJE_ERROR
    assert intentos["n"] == 1
    assert entorno["esperas"] == []


def test_otro_codigo_http_con_429_en_el_texto_no_se_reintenta(monkeypatch, entorno):
    """Un BadRequestError (400) cuyo mensaje contiene 429 no se trata como límite de uso."""

    def guion(n, proponer, listar):
        """Falla con un 400 que menciona 429 en el mensaje."""
        raise openai.BadRequestError(
            "petición inválida: referencia 429", response=_respuesta(400), body=None
        )

    intentos = correr(monkeypatch, guion)
    assert agente.responder("hola", "u1").texto == MENSAJE_ERROR
    assert intentos["n"] == 1


def test_configuracion_no_multiplica_reintentos_del_proveedor(monkeypatch, entorno):
    """El LLM y el agente no añaden reintentos propios: el bucle de `responder` es el único."""
    capturados = {}

    def kickoff(self, *args, **kwargs):
        """Guarda la configuración con la que CrewAI ejecutaría el turno."""
        capturados["max_retry_limit"] = self.agents[0].max_retry_limit
        capturados["max_retries"] = self.agents[0].llm.max_retries
        return "ok"

    monkeypatch.setattr(Crew, "kickoff", kickoff)
    agente.responder("hola", "u1")
    assert capturados == {"max_retry_limit": 0, "max_retries": 0}


def test_error_500_no_se_reintenta(monkeypatch, entorno):
    """Un error 500 del proveedor no entra en la política de reintento por límite."""

    def guion(n, proponer, listar):
        """Falla con un 500."""
        raise openai.InternalServerError("fallo interno", response=_respuesta(500), body=None)

    intentos = correr(monkeypatch, guion)
    assert agente.responder("hola", "u1").texto == MENSAJE_ERROR
    assert intentos["n"] == 1
