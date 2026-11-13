"""Concurrencia de turnos del agente: publicación condicionada y sin restauraciones.

Turnos reales de `responder()` en hilos, sincronizados con Event y Barrier (sin sleep).
Modelo y calendario simulados. Sin Groq ni Google.
"""

import threading

import pytest
from crewai import Crew

from src.agente import agente, confirmacion

DIA = ("2026-11-10T00:00:00", "2026-11-11T00:00:00")
INI_A, FIN_A = "2026-11-12T19:00:00", "2026-11-12T20:00:00"
INI, FIN = "2026-11-10T15:00:00", "2026-11-10T16:00:00"
INI2, FIN2 = "2026-11-10T17:00:00", "2026-11-10T18:00:00"
# Espera máxima de sincronización: si un evento no llega, el test falla en vez de colgarse.
TIEMPO = 5
MENSAJE_CAMBIO = confirmacion.MENSAJE_CAMBIO


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    """Estado limpio, calendario en memoria y lista de creaciones."""
    confirmacion._PENDIENTES.clear()
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("GROQ_BASE_URL", "http://localhost:9")
    creados = []
    monkeypatch.setattr(
        confirmacion.calendario,
        "crear_evento_calendario",
        lambda t, i, f: creados.append((t, i, f)) or "creado",
    )
    monkeypatch.setattr(confirmacion.calendario, "listar_eventos", lambda d, h: [])
    return creados


def comportamientos(monkeypatch):
    """Cada hilo (por nombre) ejecuta su función `(herramientas) -> texto` dentro del kickoff simulado."""
    mapa = {}

    def kickoff(self, *args, **kwargs):
        """Entrega al hilo actual las herramientas de su turno y ejecuta su comportamiento."""
        herramientas = {t.name: t for t in self.agents[0].tools}
        return mapa[threading.current_thread().name](herramientas)

    monkeypatch.setattr(Crew, "kickoff", kickoff)
    return mapa


def proponer(herramientas, titulo, inicio=INI, fin=FIN):
    """Consulta la agenda y propone, como lo haría el modelo."""
    herramientas["listar_eventos"].func(*DIA)
    return herramientas["proponer_evento_calendario"].func(titulo, inicio, fin)


def lanzar(nombre, texto, resultados):
    """Ejecuta `responder` en un hilo con el nombre dado; el resultado va a `resultados[nombre]`."""
    hilo = threading.Thread(
        target=lambda: resultados.__setitem__(nombre, agente.responder(texto, "u1")),
        name=nombre,
    )
    hilo.start()
    return hilo


def terminar(hilo):
    """Espera al hilo y falla si no termina a tiempo."""
    hilo.join(TIEMPO)
    assert not hilo.is_alive(), "el hilo no terminó: sincronización colgada"


def test_turno_fallido_no_quita_reemplazo_de_turno_concurrente(monkeypatch, entorno):
    """Un turno que falla no elimina el reemplazo que otro turno ya publicó."""
    mapa = comportamientos(monkeypatch)
    confirmacion.proponer("u1", "Gimnasio", INI_A, FIN_A)
    dentro, sigue = threading.Event(), threading.Event()

    def t1(h):
        """Propone Reunión y espera a que el turno fallido termine."""
        proponer(h, "Reunión")
        dentro.set()
        assert sigue.wait(TIEMPO)
        return "ok"

    def t2(h):
        """Propone Almuerzo y falla con un error no recuperable."""
        proponer(h, "Almuerzo", INI2, FIN2)
        raise RuntimeError("groq caído")

    mapa["T1"] = t1
    mapa["MainThread"] = t2
    resultados = {}
    hilo = lanzar("T1", "agéndame una reunión", resultados)
    assert dentro.wait(TIEMPO)
    agente.responder("agéndame un almuerzo", "u1")
    sigue.set()
    terminar(hilo)

    accion = confirmacion._PENDIENTES["u1"]
    assert accion.titulo == "Gimnasio"
    assert accion.reemplazo is not None and accion.reemplazo.titulo == "Reunión"
    assert entorno == []


def test_dos_turnos_exitosos_publican_una_sola_propuesta(monkeypatch, entorno):
    """Si dos turnos terminan bien con el mismo estado de partida, solo uno publica; el otro avisa."""
    mapa = comportamientos(monkeypatch)
    barrera = threading.Barrier(2, timeout=TIEMPO)

    def turno(titulo):
        """Propone y espera a que el otro turno también haya leído el estado."""

        def comportamiento(h):
            proponer(h, titulo)
            barrera.wait()
            return "ok"

        return comportamiento

    mapa["T1"] = turno("Reunión")
    mapa["T2"] = turno("Almuerzo")
    resultados = {}
    hilos = [lanzar("T1", "reunión", resultados), lanzar("T2", "almuerzo", resultados)]
    for hilo in hilos:
        terminar(hilo)

    avisos = [r.texto.startswith(MENSAJE_CAMBIO) for r in resultados.values()]
    assert avisos.count(True) == 1
    accion = confirmacion._PENDIENTES["u1"]
    assert accion.titulo in {"Reunión", "Almuerzo"}
    assert accion.reemplazo is None
    assert entorno == []


def test_publicacion_tardia_no_sobrescribe_propuesta_publicada_antes(monkeypatch, entorno):
    """Un turno que termina después no reemplaza la propuesta que otro turno ya publicó."""
    mapa = comportamientos(monkeypatch)
    dentro, sigue = threading.Event(), threading.Event()

    def t1(h):
        """Propone Reunión y espera; termina después de que T2 publique."""
        proponer(h, "Reunión")
        dentro.set()
        assert sigue.wait(TIEMPO)
        return "ok"

    def t2(h):
        """Propone Almuerzo y termina bien."""
        proponer(h, "Almuerzo", INI2, FIN2)
        return "ok"

    mapa["T1"] = t1
    mapa["MainThread"] = t2
    resultados = {}
    hilo = lanzar("T1", "agéndame una reunión", resultados)
    assert dentro.wait(TIEMPO)
    agente.responder("agéndame un almuerzo", "u1")
    sigue.set()
    terminar(hilo)

    assert resultados["T1"].texto.startswith(MENSAJE_CAMBIO)
    accion = confirmacion._PENDIENTES["u1"]
    assert accion.titulo == "Almuerzo"
    assert accion.reemplazo is None
    assert entorno == []


def test_propuesta_no_resucita_si_otro_turno_la_consumio(monkeypatch, entorno):
    """Una propuesta de un turno no se publica si, mientras tanto, otro turno ejecutó la pendiente."""
    mapa = comportamientos(monkeypatch)
    confirmacion.proponer("u1", "Gimnasio", INI_A, FIN_A)
    confirmacion.proponer("u2", "Clase", INI2, FIN2)
    otro = confirmacion._PENDIENTES["u2"]
    dentro, sigue = threading.Event(), threading.Event()

    def t1(h):
        """Propone Reunión y espera a que el otro turno ejecute la pendiente."""
        proponer(h, "Reunión")
        dentro.set()
        assert sigue.wait(TIEMPO)
        return "ok"

    mapa["T1"] = t1
    resultados = {}
    hilo = lanzar("T1", "agéndame una reunión", resultados)
    assert dentro.wait(TIEMPO)
    confirmada = agente.responder("sí", "u1")
    sigue.set()
    terminar(hilo)

    assert confirmada.texto == "creado"
    assert entorno == [("Gimnasio", INI_A, FIN_A)]
    assert resultados["T1"].texto.startswith(MENSAJE_CAMBIO)
    assert confirmacion.pendiente_id("u1") is None
    assert confirmacion._PENDIENTES["u2"] is otro


def test_reemplazo_aceptado_no_se_restaura_por_turno_concurrente(monkeypatch, entorno):
    """Tras aceptar un reemplazo creado durante el turno, el turno no vuelve al estado de partida."""
    mapa = comportamientos(monkeypatch)
    confirmacion.proponer("u1", "Gimnasio", INI_A, FIN_A)
    dentro, sigue = threading.Event(), threading.Event()

    def t1(h):
        """Propone Reunión y espera a que otro turno cambie la propuesta."""
        proponer(h, "Reunión")
        dentro.set()
        assert sigue.wait(TIEMPO)
        return "ok"

    mapa["T1"] = t1
    resultados = {}
    hilo = lanzar("T1", "agéndame una reunión", resultados)
    assert dentro.wait(TIEMPO)
    confirmacion.proponer("u1", "Almuerzo", INI2, FIN2)  # otro turno: Almuerzo es reemplazo de Gimnasio
    agente.responder("sí", "u1")  # acepta el reemplazo: Almuerzo queda como propuesta activa
    sigue.set()
    terminar(hilo)

    accion = confirmacion._PENDIENTES["u1"]
    assert accion.titulo == "Almuerzo"
    assert accion.reemplazo is None
    assert resultados["T1"].texto.startswith(MENSAJE_CAMBIO)
    assert entorno == []


def test_turno_sin_propuestas_no_falla_por_cambio_concurrente(monkeypatch, entorno):
    """Un turno que no propone nada responde normalmente aunque el estado haya cambiado."""
    mapa = comportamientos(monkeypatch)
    confirmacion.proponer("u1", "Gimnasio", INI_A, FIN_A)
    dentro, sigue = threading.Event(), threading.Event()

    def t1(h):
        """Solo conversa y espera a que el otro turno cambie el estado."""
        dentro.set()
        assert sigue.wait(TIEMPO)
        return "Hola"

    mapa["T1"] = t1
    resultados = {}
    hilo = lanzar("T1", "hola", resultados)
    assert dentro.wait(TIEMPO)
    agente.responder("no", "u1")  # cancela Gimnasio
    sigue.set()
    terminar(hilo)

    assert resultados["T1"].texto == "Hola"
    assert confirmacion.pendiente_id("u1") is None
    assert entorno == []
