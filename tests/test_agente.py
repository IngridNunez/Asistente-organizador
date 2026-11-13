from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.agente import confirmacion
from src.agente.agente import _crear_llm, responder
from src.agente.prompt import ZONA_HORARIA, construir_prompt_sistema, saludo_del_momento
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


def ahora_en(hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 11, 13, hora, minuto, tzinfo=ZoneInfo(ZONA_HORARIA))


# Franjas horarias deterministas: el reloj es el de la prueba, no el de la ejecución
@pytest.mark.parametrize(
    "hora, minuto, saludo",
    [
        (0, 0, "Buenos días"),
        (9, 0, "Buenos días"),
        (11, 59, "Buenos días"),
        (12, 0, "Buenas tardes"),
        (15, 0, "Buenas tardes"),
        (19, 59, "Buenas tardes"),
        (20, 0, "Buenas noches"),
        (21, 0, "Buenas noches"),
        (23, 59, "Buenas noches"),
    ],
)
def test_saludo_por_franja_horaria(hora, minuto, saludo):
    assert saludo_del_momento(ahora_en(hora, minuto)) == saludo
    assert f"Franja horaria actual: {saludo}." in construir_prompt_sistema(
        ahora_en(hora, minuto)
    )


# Pruebas estructurales: fijan intenciones clave del prompt, no la redacción exacta
def test_prompt_identidad_y_personalidad():
    prompt = construir_prompt_sistema(ahora_en(15))
    assert "Eres Sara" in prompt
    assert "Soy Sara, tu Sistema de Agendamiento y Reserva de Actividades." in prompt
    for rasgo in ("calmada", "cercana", "animada"):
        assert rasgo in prompt
    assert "CITT de Duoc UC" in prompt
    assert "No eres un servicio institucional" in prompt
    assert "No tienes emociones" in prompt


def test_prompt_tts_y_tuteo():
    prompt = construir_prompt_sistema(ahora_en(15))
    assert "Escribe Sara en tus respuestas, no la sigla" in prompt
    assert "Usa la sigla S.A.R.A. solo si preguntan" in prompt
    assert "tienes" in prompt and "quieres" in prompt and "puedes" in prompt
    assert "Nunca uses voseo" in prompt
    assert "tenés" not in prompt and "querés" not in prompt and "podés" not in prompt
    assert "No uses Markdown" in prompt


def test_prompt_humor_restringido():
    prompt = construir_prompt_sistema(ahora_en(15))
    assert "Nunca uses humor ni sarcasmo en confirmaciones, errores" in prompt
    assert "Nunca te burles del usuario" in prompt


def test_prompt_consulta_agenda_antes_de_proponer():
    prompt = construir_prompt_sistema(ahora_en(15))
    assert "Antes de proponer un evento" in prompt
    assert "herramienta de listar eventos" in prompt
    assert "cruce de horario" in prompt


def test_prompt_confirmacion_y_exito_de_herramienta():
    prompt = construir_prompt_sistema(ahora_en(15))
    assert "¿La confirmo?" in prompt
    assert "Autorizar no es lo mismo que ejecutar" in prompt
    assert "resultado satisfactorio de la herramienta" in prompt


def test_prompt_cierre_condicionado():
    prompt = construir_prompt_sistema(ahora_en(15))
    assert "Usa \"¿Algo más?\" solo tras completar una tarea" in prompt
    assert "confirmación pendiente" in prompt


def test_prompt_limites_sin_reservas_inexistentes():
    prompt = construir_prompt_sistema(ahora_en(15))
    assert "No puedes reservar salas" in prompt
    assert "Eso no lo puedo hacer" in prompt
