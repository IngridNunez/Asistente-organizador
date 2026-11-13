"""Fase 3: reemplazo en dos etapas, expiración informada y transiciones concurrentes.

Concurrencia determinista: barreras y eventos, sin sleep arbitrario. Calendario simulado.
"""

import threading

import pytest

from src.agente import confirmacion

A = ("Reunión", "2026-11-10T10:00:00", "2026-11-10T11:00:00")
B = ("Almuerzo", "2026-11-11T15:00:00", "2026-11-11T16:00:00")
C = ("Gimnasio", "2026-11-12T19:00:00", "2026-11-12T20:00:00")


@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    confirmacion._PENDIENTES.clear()
    creados = []

    def crear(titulo, inicio, fin):
        creados.append((titulo, inicio, fin))
        return "creado"

    monkeypatch.setattr(confirmacion.calendario, "crear_evento_calendario", crear)
    return creados


@pytest.fixture
def reloj(monkeypatch):
    """Reloj monotónico simulado: `reloj.t` avanza a voluntad."""

    class Reloj:
        t = 1000.0

    r = Reloj()
    monkeypatch.setattr(confirmacion.time, "monotonic", lambda: r.t)
    return r


def _proponer(p):
    return confirmacion.proponer("u1", p[0], p[1], p[2])


# --- Reemplazo en dos etapas ---


def test_segunda_propuesta_pide_reemplazo_sin_ejecutar_nada(limpio):
    _proponer(A)
    id_b = _proponer(B)
    assert confirmacion.pendiente_id("u1") == id_b
    assert "¿Lo reemplazo por Almuerzo" in confirmacion.resumen("u1")
    assert limpio == []


def test_primer_si_activa_b_sin_crear(limpio):
    _proponer(A)
    _proponer(B)
    texto = confirmacion.resolver("u1", "sí", confirmacion.pendiente_id("u1"))
    assert texto.startswith("Puedo registrar Almuerzo")
    assert texto.endswith("¿La confirmo?")
    assert limpio == []


def test_segundo_si_ejecuta_b_y_no_a(limpio):
    _proponer(A)
    _proponer(B)
    confirmacion.resolver("u1", "sí", confirmacion.pendiente_id("u1"))
    assert confirmacion.resolver("u1", "sí", confirmacion.pendiente_id("u1")) == "creado"
    assert limpio == [B]


def test_rechazo_del_reemplazo_conserva_a(limpio):
    _proponer(A)
    _proponer(B)
    assert confirmacion.resolver("u1", "no", confirmacion.pendiente_id("u1")) == (
        "Listo, mantengo la propuesta anterior."
    )
    assert confirmacion.resolver("u1", "sí", confirmacion.pendiente_id("u1")) == "creado"
    assert limpio == [A]


def test_mensaje_ajeno_en_reemplazo_descarta_b_y_conserva_a(limpio):
    _proponer(A)
    _proponer(B)
    assert confirmacion.resolver("u1", "qué hora es", confirmacion.pendiente_id("u1")) is None
    assert confirmacion.resolver("u1", "sí", confirmacion.pendiente_id("u1")) == "creado"
    assert limpio == [A]


def test_propuesta_invalida_durante_reemplazo_conserva_a(limpio):
    id_a = _proponer(A)
    with pytest.raises(ValueError):
        confirmacion.proponer("u1", "", B[1], B[2])
    assert confirmacion.pendiente_id("u1") == id_a
    assert confirmacion.resolver("u1", "sí", id_a) == "creado"
    assert limpio == [A]


# --- Expiración ---


def test_propuesta_expirada_informa_y_no_crea(limpio, reloj):
    _proponer(A)
    reloj.t += confirmacion.TTL_SEGUNDOS + 1
    assert confirmacion.resolver("u1", "sí") == confirmacion.MENSAJE_VENCIDA
    assert limpio == []


def test_si_tardio_tras_consumir_no_vuelve_a_crear(limpio):
    _proponer(A)
    assert confirmacion.resolver("u1", "sí") == "creado"
    assert confirmacion.resolver("u1", "sí") is None
    assert limpio == [A]


def test_a_expirada_durante_reemplazo_no_ejecuta_b(limpio, reloj):
    _proponer(A)
    reloj.t += 200
    _proponer(B)
    reloj.t += 150  # A venció (350 s); B aún no
    assert confirmacion.resolver("u1", "sí", confirmacion.pendiente_id("u1")) == (
        confirmacion.MENSAJE_VENCIDA
    )
    assert confirmacion.pendiente_id("u1") is None
    assert limpio == []


def test_b_no_puede_sobrevivir_a_a_en_el_reemplazo(limpio, reloj):
    # B se propone después que A, así que vence después: el reemplazo nunca queda huérfano.
    _proponer(A)
    reloj.t += 200
    _proponer(B)
    reloj.t += 101
    assert confirmacion.pendiente_id("u1") is None


def test_propuesta_vencida_no_se_reactiva_tras_nueva_propuesta(limpio, reloj):
    _proponer(A)
    reloj.t += confirmacion.TTL_SEGUNDOS + 1
    _proponer(B)  # A vencida no pide reemplazo: B es la única pendiente
    assert confirmacion.resolver("u1", "sí", confirmacion.pendiente_id("u1")) == "creado"
    assert limpio == [B]


# --- Concurrencia ---


def test_n_hilos_confirmando_crean_una_sola_vez(limpio):
    id_ = _proponer(A)
    n = 8
    barrera = threading.Barrier(n)
    resultados = []

    def confirmar():
        barrera.wait()
        resultados.append(confirmacion.resolver("u1", "sí", id_))

    hilos = [threading.Thread(target=confirmar) for _ in range(n)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=5)
    assert len(limpio) == 1
    assert resultados.count("creado") == 1


def test_dos_si_simultaneos_en_etapa_de_reemplazo_no_ejecutan_b(limpio):
    _proponer(A)
    _proponer(B)
    visto = confirmacion.pendiente_id("u1")
    barrera = threading.Barrier(2)
    resultados = []

    def confirmar():
        barrera.wait()
        resultados.append(confirmacion.resolver("u1", "sí", visto))

    hilos = [threading.Thread(target=confirmar) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=5)
    # Un solo "sí" activa B; el otro llega con la etapa ya cambiada y no autoriza nada.
    assert limpio == []
    assert resultados.count(confirmacion.MENSAJE_CAMBIO) == 1
    assert confirmacion.resolver("u1", "sí", confirmacion.pendiente_id("u1")) == "creado"
    assert limpio == [B]


def test_no_sobrescribe_propuesta_nueva_durante_ejecucion(limpio, monkeypatch):
    id_a = _proponer(A)
    en_calendario = threading.Event()
    liberar = threading.Event()

    def crear_lento(titulo, inicio, fin):
        en_calendario.set()
        liberar.wait(timeout=5)
        return "creado"

    monkeypatch.setattr(confirmacion.calendario, "crear_evento_calendario", crear_lento)
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(confirmacion.resolver("u1", "sí", id_a)))
    hilo.start()
    assert en_calendario.wait(timeout=5)
    # El calendario todavía no respondió: el usuario propone otra cosa.
    id_c = _proponer(C)
    liberar.set()
    hilo.join(timeout=5)
    assert resultado == ["creado"]
    assert confirmacion.pendiente_id("u1") == id_c


def test_calendario_no_bloquea_el_lock(monkeypatch):
    _proponer(A)
    id_ = confirmacion.pendiente_id("u1")
    consulta = {}

    def crear_que_consulta(titulo, inicio, fin):
        # Si el lock siguiera tomado aquí, esta llamada se bloquearía y el test expiraría.
        hilo = threading.Thread(target=lambda: consulta.update(id=confirmacion.pendiente_id("u2")))
        hilo.start()
        hilo.join(timeout=5)
        return "creado" if not hilo.is_alive() else "bloqueado"

    monkeypatch.setattr(confirmacion.calendario, "crear_evento_calendario", crear_que_consulta)
    assert confirmacion.resolver("u1", "sí", id_) == "creado"


def test_fallo_de_calendario_tras_confirmar_no_dice_exito(limpio, monkeypatch):
    _proponer(A)

    def falla(*args):
        raise ConnectionError("sin red")

    monkeypatch.setattr(confirmacion.calendario, "crear_evento_calendario", falla)
    texto = confirmacion.resolver("u1", "sí")
    assert texto == "No pude crear el evento. Intenta de nuevo en un momento."
    assert "creé" not in texto and "creado" not in texto
