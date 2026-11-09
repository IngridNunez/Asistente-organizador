import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime

# Único punto donde el agente toca el calendario (tools.py lo reutiliza desde aquí).
# Usa el calendario real (Google Calendar). Para volver al stub: calendario_falso as calendario.
from src.herramientas import calendario

log = logging.getLogger(__name__)

# Una acción propuesta caduca a los 5 minutos: una confirmación vieja no debe ejecutar nada.
TTL_SEGUNDOS = 300

# Palabras que cuentan como "sí". El mensaje debe traer al menos una de NUCLEO_SI y
# ninguna palabra fuera de las dos listas: "gracias" solo no confirma, y
# "sí, pero a las 6" se trata como un pedido nuevo, no como confirmación.
NUCLEO_SI = {
    "si",
    "sí",
    "confirmo",
    "confirmado",
    "dale",
    "ok",
    "okay",
    "claro",
    "correcto",
    "perfecto",
    "adelante",
    "hazlo",
    "crealo",
    "créalo",
    "confirmalo",
    "confírmalo",
}
RELLENO = {"por", "favor", "gracias"}
PALABRAS_NO = {
    "no",
    "cancela",
    "cancelar",
    "cancelalo",
    "cancélalo",
    "olvidalo",
    "olvídalo",
}
# Un "no" largo ("no, mejor a las 6") es una corrección, no una cancelación: va al modelo.
MAX_PALABRAS_NO = 3
MAX_PALABRAS_SI = 5


@dataclass
class AccionPendiente:
    id: str
    titulo: str
    inicio: str
    fin: str
    creada: float


# Estado en memoria del agente (etapas 1-4, todo corre en un proceso): usuario_id -> acción pendiente.
# Con varios procesos o el celular remoto esto debe moverse a un almacén compartido.
_PENDIENTES: dict[str, AccionPendiente] = {}


def _palabras(texto: str) -> list[str]:
    return re.findall(r"\w+", texto.lower())


def _purgar_vencidas() -> None:
    """Borra las propuestas vencidas de todos los usuarios, para que el dict no crezca sin límite."""
    ahora = time.monotonic()
    for usuario, accion in list(_PENDIENTES.items()):
        if ahora - accion.creada > TTL_SEGUNDOS:
            _PENDIENTES.pop(usuario, None)


def _validar_fechas(inicio: str, fin: str) -> None:
    """Valida las fechas de una propuesta.

    Falla ahora para que el error llegue al modelo y no recién cuando el usuario ya confirmó.

    Raises:
        ValueError: si no son ISO 8601, mezclan zonas horarias o `fin` no es posterior a `inicio`.
    """
    try:
        desde = datetime.fromisoformat(inicio)
        hasta = datetime.fromisoformat(fin)
    except ValueError:
        raise ValueError("inicio y fin deben ir en formato ISO 8601") from None
    if (desde.tzinfo is None) != (hasta.tzinfo is None):
        raise ValueError("inicio y fin deben usar la misma zona horaria")
    if hasta <= desde:
        raise ValueError("fin debe ser posterior a inicio")


def proponer(usuario_id: str, titulo: str, inicio: str, fin: str) -> str:
    """Registra una propuesta de evento. La tool del agente llama aquí.

    NO crea nada: solo deja la propuesta esperando el "sí". Reemplaza la pendiente anterior
    del mismo usuario.

    Returns:
        El id de la acción pendiente.

    Raises:
        ValueError: si las fechas no son válidas (ver `_validar_fechas`).
    """
    _validar_fechas(inicio, fin)
    _purgar_vencidas()
    accion = AccionPendiente(
        uuid.uuid4().hex[:8], titulo, inicio, fin, time.monotonic()
    )
    _PENDIENTES[usuario_id] = accion
    return accion.id


def descartar(usuario_id: str) -> None:
    """Elimina la acción pendiente del usuario, si existe."""
    _PENDIENTES.pop(usuario_id, None)


def pendiente_id(usuario_id: str) -> str | None:
    """Devuelve el id de la acción pendiente del usuario, o None si no hay."""
    accion = _PENDIENTES.get(usuario_id)
    return accion.id if accion else None


def resolver(usuario_id: str, texto: str) -> str | None:
    """Resuelve la confirmación pendiente del usuario. Se llama al inicio de cada turno.

    Siempre consume la acción pendiente (vale una sola vez). Un "sí" explícito crea el evento;
    un "no" corto lo cancela. Si la propuesta venció o el mensaje es otra cosa, devuelve None.

    Returns:
        El texto a decir si el mensaje era un sí/no explícito; None si hay que seguir normal.
    """
    accion = _PENDIENTES.pop(usuario_id, None)
    if accion is None:
        return None
    if time.monotonic() - accion.creada > TTL_SEGUNDOS:
        return None

    palabras = _palabras(texto)
    if not palabras:
        return None
    if palabras[0] in PALABRAS_NO and len(palabras) <= MAX_PALABRAS_NO:
        return "Listo, no lo creé."
    if (
        len(palabras) <= MAX_PALABRAS_SI
        and any(p in NUCLEO_SI for p in palabras)
        and all(p in NUCLEO_SI or p in RELLENO for p in palabras)
    ):
        try:
            return calendario.crear_evento_calendario(
                accion.titulo, accion.inicio, accion.fin
            )
        except Exception as e:
            # El calendario real puede fallar (red, permisos): se avisa, no se tumba la petición.
            log.error("Falló la creación del evento: %s", e)
            return "No pude crear el evento. Intenta de nuevo en un momento."
    return None
