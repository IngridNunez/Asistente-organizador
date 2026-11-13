"""Fase 2: una propuesta solo se guarda si el mismo turno consultó la agenda que la cubre."""

import json

import pytest

from src.agente import confirmacion
from src.agente.tools import construir_tools

INI = "2026-11-10T15:00:00"
FIN = "2026-11-10T16:00:00"
DIA = ("2026-11-10T00:00:00", "2026-11-11T00:00:00")


@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    confirmacion._PENDIENTES.clear()
    creados = []
    monkeypatch.setattr(
        confirmacion.calendario,
        "crear_evento_calendario",
        lambda t, i, f: creados.append((t, i, f)) or "creado",
    )
    return creados


def _evento(inicio, fin, titulo="Otra"):
    return {"titulo": titulo, "inicio": inicio, "fin": fin}


def _agenda(monkeypatch, eventos):
    monkeypatch.setattr(confirmacion.calendario, "listar_eventos", lambda d, h: eventos)


def _turno(usuario="u1"):
    proponer, listar = construir_tools(usuario)
    return proponer, listar


def test_propuesta_sin_consulta_no_se_guarda(limpio):
    proponer, _ = _turno()
    resultado = proponer.func("Reunión", INI, FIN)
    assert resultado.startswith("Error: no he consultado la agenda")
    assert confirmacion.pendiente_id("u1") is None
    assert limpio == []


def test_consulta_exitosa_que_cubre_permite_proponer(monkeypatch):
    _agenda(monkeypatch, [])
    proponer, listar = _turno()
    listar.func(*DIA)
    assert proponer.func("Reunión", INI, FIN).startswith("Propuesta registrada")
    assert confirmacion.pendiente_id("u1") is not None


def test_consulta_de_otro_dia_no_habilita(monkeypatch):
    _agenda(monkeypatch, [])
    proponer, listar = _turno()
    listar.func("2026-11-09T00:00:00", "2026-11-10T00:00:00")
    assert proponer.func("Reunión", INI, FIN).startswith("Error:")
    assert confirmacion.pendiente_id("u1") is None


def test_consulta_de_otro_usuario_no_habilita(monkeypatch):
    _agenda(monkeypatch, [])
    _, listar_u2 = _turno("u2")
    listar_u2.func(*DIA)
    proponer_u1, _ = _turno("u1")
    assert proponer_u1.func("Reunión", INI, FIN).startswith("Error:")


def test_consulta_de_otro_turno_no_habilita(monkeypatch):
    _agenda(monkeypatch, [])
    _, listar_turno_1 = _turno()
    listar_turno_1.func(*DIA)
    proponer_turno_2, _ = _turno()
    assert proponer_turno_2.func("Reunión", INI, FIN).startswith("Error:")


def test_consulta_que_cubre_solo_parte_no_habilita(monkeypatch):
    _agenda(monkeypatch, [])
    proponer, listar = _turno()
    listar.func("2026-11-10T09:00:00", "2026-11-10T10:00:00")
    assert proponer.func(
        "Reunión", "2026-11-10T09:00:00", "2026-11-10T12:00:00"
    ).startswith("Error:")


def test_propuesta_que_empieza_y_termina_en_los_limites_se_acepta(monkeypatch):
    _agenda(monkeypatch, [])
    proponer, listar = _turno()
    listar.func(INI, FIN)
    assert proponer.func("Reunión", INI, FIN).startswith("Propuesta registrada")


def test_consulta_fallida_no_habilita_ni_se_confunde_con_agenda_vacia(monkeypatch):
    def falla(d, h):
        raise ConnectionError("sin red")

    monkeypatch.setattr(confirmacion.calendario, "listar_eventos", falla)
    proponer, listar = _turno()
    assert listar.func(*DIA).startswith("Error: no pude leer el calendario")
    assert proponer.func("Reunión", INI, FIN).startswith("Error:")


def test_evento_no_interpretable_no_se_afirma_libre(monkeypatch):
    _agenda(monkeypatch, [{"titulo": "x", "inicio": None, "fin": None}])
    proponer, listar = _turno()
    assert listar.func(*DIA).startswith("Error: no pude interpretar")
    assert proponer.func("Reunión", INI, FIN).startswith("Error:")


def test_resultado_truncado_no_habilita(monkeypatch):
    eventos = [_evento("2026-11-10T08:00:00-03:00", "2026-11-10T08:30:00-03:00")] * 50
    _agenda(monkeypatch, eventos)
    proponer, listar = _turno()
    assert listar.func(*DIA).startswith("Error: hay 50 o más eventos")
    assert proponer.func("Reunión", INI, FIN).startswith("Error:")


def test_agenda_vacia_consultada_permite_sin_advertencias(monkeypatch):
    _agenda(monkeypatch, [])
    proponer, listar = _turno()
    listar.func(*DIA)
    proponer.func("Reunión", INI, FIN)
    assert confirmacion.resumen("u1") == (
        "Puedo registrar Reunión el 10/11 de 15:00 a 16:00. ¿La confirmo?"
    )


def test_conflicto_se_avisa_en_el_resumen(monkeypatch):
    _agenda(monkeypatch, [_evento("2026-11-10T15:30:00-03:00", "2026-11-10T16:30:00-03:00")])
    proponer, listar = _turno()
    listar.func(*DIA)
    proponer.func("Reunión", INI, FIN)
    resumen = confirmacion.resumen("u1")
    assert "Coincide con otra actividad de 15:30 a 16:30." in resumen
    assert resumen.endswith("¿La confirmo?")


def test_evento_consecutivo_no_es_conflicto(monkeypatch):
    _agenda(monkeypatch, [_evento("2026-11-10T16:00:00-03:00", "2026-11-10T17:00:00-03:00")])
    proponer, listar = _turno()
    listar.func(*DIA)
    proponer.func("Reunión", INI, FIN)
    assert "Coincide" not in confirmacion.resumen("u1")


def test_dia_completo_se_avisa_como_tal(monkeypatch):
    _agenda(monkeypatch, [_evento("2026-11-10", "2026-11-11", "Feriado")])
    proponer, listar = _turno()
    listar.func(*DIA)
    proponer.func("Reunión", INI, FIN)
    assert "Coincide con un evento de día completo." in confirmacion.resumen("u1")


def test_propuesta_invalida_conserva_la_pendiente_valida(monkeypatch):
    _agenda(monkeypatch, [])
    proponer, listar = _turno()
    listar.func(*DIA)
    proponer.func("Reunión", INI, FIN)
    id_valido = confirmacion.pendiente_id("u1")
    assert proponer.func("", INI, FIN).startswith("Error:")
    assert proponer.func(
        "Otra", "2026-11-10T20:00:00", "2026-11-10T19:00:00"
    ).startswith("Error:")
    assert confirmacion.pendiente_id("u1") == id_valido


def test_turnos_independientes_no_comparten_consultas(monkeypatch):
    _agenda(monkeypatch, [])
    proponer_a, listar_a = _turno()
    proponer_b, _ = _turno()
    listar_a.func(*DIA)
    assert proponer_a.func("Reunión", INI, FIN).startswith("Propuesta registrada")
    confirmacion._PENDIENTES.clear()
    assert proponer_b.func("Reunión", INI, FIN).startswith("Error:")


def test_consulta_con_offsets_distintos_se_compara_por_instante(monkeypatch):
    # 14:00-04:00 equivale a 15:00-03:00: la consulta cubre la propuesta aunque cambie el offset
    _agenda(monkeypatch, [])
    proponer, listar = _turno()
    listar.func("2026-11-10T14:00:00-04:00", "2026-11-10T17:00:00-04:00")
    assert proponer.func(
        "Reunión", "2026-11-10T15:00:00-03:00", "2026-11-10T16:00:00-03:00"
    ).startswith("Propuesta registrada")


def test_cambio_de_horario_de_verano_chile(monkeypatch):
    # En Chile el horario de verano termina el primer sábado de abril de 2026 (2026-04-04)
    _agenda(monkeypatch, [])
    proponer, listar = _turno()
    listar.func("2026-04-04T00:00:00", "2026-04-06T00:00:00")
    assert proponer.func(
        "Reunión", "2026-04-04T23:00:00", "2026-04-05T01:00:00"
    ).startswith("Propuesta registrada")


def test_listar_devuelve_los_eventos_sin_cambios(monkeypatch):
    eventos = [_evento(INI, FIN, "Otra")]
    _agenda(monkeypatch, eventos)
    _, listar = _turno()
    assert json.loads(listar.func(*DIA))["eventos"] == eventos


A = confirmacion.instante


@pytest.mark.parametrize(
    "a, b, esperado",
    [
        (("2026-11-10T10:00:00", "2026-11-10T11:00:00"), ("2026-11-10T11:00:00", "2026-11-10T12:00:00"), False),  # consecutivos
        (("2026-11-10T10:00:00", "2026-11-10T11:30:00"), ("2026-11-10T11:00:00", "2026-11-10T12:00:00"), True),  # parcial
        (("2026-11-10T10:00:00", "2026-11-10T13:00:00"), ("2026-11-10T11:00:00", "2026-11-10T12:00:00"), True),  # contenido
        (("2026-11-10T10:00:00", "2026-11-10T11:00:00"), ("2026-11-10T10:00:00", "2026-11-10T11:00:00"), True),  # exacta
        (("2026-11-10T23:00:00", "2026-11-11T01:00:00"), ("2026-11-11T00:00:00", "2026-11-11T00:30:00"), True),  # medianoche
        (("2026-11-10T10:00:00-03:00", "2026-11-10T11:00:00-03:00"), ("2026-11-10T09:30:00-04:00", "2026-11-10T10:30:00-04:00"), True),  # offsets: 13:00-14:00 UTC vs 13:30-14:30 UTC
    ],
)
def test_hay_solapamiento(a, b, esperado):
    assert confirmacion.hay_solapamiento(A(a[0]), A(a[1]), A(b[0]), A(b[1])) is esperado
