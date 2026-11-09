import pytest

from src.agente import memoria
from src.agente.memoria import (
    MAX_CONVERSACIONES,
    TurnoConversacion,
    cantidad_conversaciones,
    guardar_turno,
    limpiar_memoria,
    obtener_historial,
    obtener_historial_formateado,
)


@pytest.fixture(autouse=True)
def limpiar_estado():
    """Garantiza que cada test empiece con la memoria vacía."""
    limpiar_memoria()
    yield
    limpiar_memoria()


def test_guardar_primer_turno():
    guardar_turno("u1", "¿Qué hora es?", "Son las 10:00 AM.")
    assert cantidad_conversaciones("u1") == 1

    historial = obtener_historial("u1")
    assert len(historial) == 1
    assert historial[0].usuario == "¿Qué hora es?"
    assert historial[0].asistente == "Son las 10:00 AM."


def test_guardar_hasta_tres_conversaciones():
    guardar_turno("u1", "Hola", "Hola, ¿en qué te ayudo?")
    guardar_turno("u1", "Tengo reunión a las 3", "Anotado en calendario.")
    guardar_turno("u1", "Gracias", "De nada.")

    assert cantidad_conversaciones("u1") == 3
    historial = obtener_historial("u1")
    assert len(historial) == 3
    assert historial[0].usuario == "Hola"
    assert historial[1].usuario == "Tengo reunión a las 3"
    assert historial[2].usuario == "Gracias"


def test_ventana_deslizante_descarta_conversacion_mas_antigua_al_superar_tres():
    # Insertar 3 turnos
    guardar_turno("u1", "Turno 1", "Resp 1")
    guardar_turno("u1", "Turno 2", "Resp 2")
    guardar_turno("u1", "Turno 3", "Resp 3")
    assert cantidad_conversaciones("u1") == MAX_CONVERSACIONES

    # Insertar un 4to turno: debe descartar Turno 1
    guardar_turno("u1", "Turno 4", "Resp 4")
    assert cantidad_conversaciones("u1") == 3

    historial = obtener_historial("u1")
    assert len(historial) == 3
    assert historial[0].usuario == "Turno 2"
    assert historial[1].usuario == "Turno 3"
    assert historial[2].usuario == "Turno 4"

    # Insertar un 5to turno: debe descartar Turno 2
    guardar_turno("u1", "Turno 5", "Resp 5")
    historial = obtener_historial("u1")
    assert [t.usuario for t in historial] == ["Turno 3", "Turno 4", "Turno 5"]


def test_aislamiento_entre_usuarios():
    guardar_turno("usuario_a", "Mensaje A", "Respuesta A")
    guardar_turno("usuario_b", "Mensaje B1", "Respuesta B1")
    guardar_turno("usuario_b", "Mensaje B2", "Respuesta B2")

    assert cantidad_conversaciones("usuario_a") == 1
    assert cantidad_conversaciones("usuario_b") == 2

    historial_a = obtener_historial("usuario_a")
    historial_b = obtener_historial("usuario_b")

    assert historial_a[0].usuario == "Mensaje A"
    assert [t.usuario for t in historial_b] == ["Mensaje B1", "Mensaje B2"]


def test_historial_formateado():
    assert obtener_historial_formateado("u_inexistente") == ""

    guardar_turno("u1", "Hola", "Buenas tardes.")
    guardar_turno("u1", "¿Qué tiempo hace?", "Está soleado.")

    esperado = (
        "Usuario: Hola\n"
        "Asistente: Buenas tardes.\n"
        "Usuario: ¿Qué tiempo hace?\n"
        "Asistente: Está soleado."
    )
    assert obtener_historial_formateado("u1") == esperado


def test_usuario_id_vacio_no_guarda():
    guardar_turno("", "Hola", "Mundo")
    guardar_turno("   ", "Hola", "Mundo")
    assert cantidad_conversaciones("") == 0
    assert len(memoria._HISTORIAL) == 0


def test_limpiar_memoria_por_usuario():
    guardar_turno("u1", "Hola", "Respuesta")
    guardar_turno("u2", "Hola 2", "Respuesta 2")

    limpiar_memoria("u1")
    assert cantidad_conversaciones("u1") == 0
    assert cantidad_conversaciones("u2") == 1

    limpiar_memoria()
    assert cantidad_conversaciones("u2") == 0


def test_turno_to_dict():
    turno = TurnoConversacion(usuario="Pregunta", asistente="Respuesta")
    d = turno.to_dict()
    assert d["usuario"] == "Pregunta"
    assert d["asistente"] == "Respuesta"
    assert "fecha" in d
