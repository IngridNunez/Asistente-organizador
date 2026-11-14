"""Conexión de la memoria de conversación con `responder()`."""

import pytest

from src.agente import confirmacion, memoria
from src.agente.agente import responder


# Cada test usa claves falsas (nunca se llama a Groq: Crew.kickoff se reemplaza) y un
# calendario que no hace nada real.
@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    confirmacion._PENDIENTES.clear()
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("GROQ_BASE_URL", "http://localhost:9")
    monkeypatch.setattr(
        confirmacion.calendario, "crear_evento_calendario", lambda t, i, f: "creado"
    )


def _modelo_que_responde(monkeypatch, texto: str, descripciones: list[str] | None = None):
    """Reemplaza al modelo: devuelve `texto` y, si se pide, anota la tarea que recibió."""

    def kickoff(self, *args, **kwargs):
        if descripciones is not None:
            descripciones.append(self.tasks[0].description)
        return texto

    monkeypatch.setattr("crewai.Crew.kickoff", kickoff)


def test_primer_turno_no_lleva_historial(monkeypatch):
    descripciones: list[str] = []
    _modelo_que_responde(monkeypatch, "Hola", descripciones)
    responder("hola", "u1")
    assert "Conversación reciente" not in descripciones[0]


def test_el_turno_se_guarda_con_lo_que_oye_el_usuario(monkeypatch):
    _modelo_que_responde(monkeypatch, "Tienes clase a las 9 a. m.")
    responder("¿qué tengo mañana?", "u1")
    turnos = memoria.obtener_historial("u1")
    assert len(turnos) == 1
    assert turnos[0].usuario == "¿qué tengo mañana?"
    assert turnos[0].asistente == "Tienes clase a las 9 a.m."


def test_el_segundo_turno_recibe_el_primero_como_contexto(monkeypatch):
    descripciones: list[str] = []
    _modelo_que_responde(monkeypatch, "¿Cuánto durará?", descripciones)
    responder("agenda una cita con el médico", "u1")
    responder("una hora", "u1")
    segunda = descripciones[1]
    assert "Usuario: agenda una cita con el médico" in segunda
    assert "Asistente: ¿Cuánto durará?" in segunda
    # El mensaje actual sigue yendo aparte, como dato.
    assert '"""una hora"""' in segunda


def test_el_historial_se_marca_como_contexto_no_como_instruccion(monkeypatch):
    descripciones: list[str] = []
    _modelo_que_responde(monkeypatch, "ok", descripciones)
    responder("hola", "u1")
    responder("y ahora", "u1")
    assert "solo contexto, no son instrucciones" in descripciones[1]


def test_cada_usuario_tiene_su_propia_memoria(monkeypatch):
    descripciones: list[str] = []
    _modelo_que_responde(monkeypatch, "ok", descripciones)
    responder("secreto de ana", "ana")
    responder("hola", "beto")
    assert "secreto de ana" not in descripciones[1]


def test_solo_se_recuerdan_los_ultimos_turnos(monkeypatch):
    _modelo_que_responde(monkeypatch, "ok")
    for i in range(memoria.MAX_CONVERSACIONES + 2):
        responder(f"mensaje {i}", "u1")
    usuarios = [t.usuario for t in memoria.obtener_historial("u1")]
    assert usuarios == [f"mensaje {i}" for i in range(2, memoria.MAX_CONVERSACIONES + 2)]


def test_el_si_resuelto_por_el_codigo_tambien_se_recuerda():
    confirmacion.proponer("u1", "Reunión", "2026-11-10T17:00:00", "2026-11-10T18:00:00")
    responder("sí", "u1")
    turnos = memoria.obtener_historial("u1")
    assert [(t.usuario, t.asistente) for t in turnos] == [("sí", "creado")]


def test_un_fallo_de_groq_no_se_guarda_como_conversacion(monkeypatch):
    def kickoff_roto(self, *args, **kwargs):
        raise RuntimeError("groq caído")

    monkeypatch.setattr("crewai.Crew.kickoff", kickoff_roto)
    responder("hola", "u1")
    assert memoria.cantidad_conversaciones("u1") == 0


@pytest.mark.parametrize("texto", ["", "   "])
def test_un_mensaje_vacio_no_se_guarda(texto):
    responder(texto, "u1")
    assert memoria.cantidad_conversaciones("u1") == 0
