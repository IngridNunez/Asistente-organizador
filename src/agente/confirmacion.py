import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime

# Único punto donde el agente toca el calendario (tools.py lo reutiliza desde aquí).
# Hoy es la versión "_falso": cuando Herramientas termine la real, solo cambia este import.
from src.herramientas import calendario_falso as calendario

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


# Borra las propuestas vencidas de todos los usuarios, para que el dict no crezca sin límite.
def _purgar_vencidas() -> None:
    ahora = time.monotonic()
    for usuario, accion in list(_PENDIENTES.items()):
        if ahora - accion.creada > TTL_SEGUNDOS:
            _PENDIENTES.pop(usuario, None)


# Falla con ValueError si las fechas no sirven, para que el error llegue al modelo ahora
# y no recién cuando el usuario ya confirmó.
def _validar_fechas(inicio: str, fin: str) -> None:
    try:
        desde = datetime.fromisoformat(inicio)
        hasta = datetime.fromisoformat(fin)
    except ValueError:
        raise ValueError("inicio y fin deben ir en formato ISO 8601") from None
    if (desde.tzinfo is None) != (hasta.tzinfo is None):
        raise ValueError("inicio y fin deben usar la misma zona horaria")
    if hasta <= desde:
        raise ValueError("fin debe ser posterior a inicio")


# La herramienta del agente llama aquí: NO crea nada, solo deja la propuesta esperando el "sí".
def proponer(usuario_id: str, titulo: str, inicio: str, fin: str) -> str:
    _validar_fechas(inicio, fin)
    _purgar_vencidas()
    accion = AccionPendiente(
        uuid.uuid4().hex[:8], titulo, inicio, fin, time.monotonic()
    )
    _PENDIENTES[usuario_id] = accion
    return accion.id


def descartar(usuario_id: str) -> None:
    _PENDIENTES.pop(usuario_id, None)


def pendiente_id(usuario_id: str) -> str | None:
    accion = _PENDIENTES.get(usuario_id)
    return accion.id if accion else None


# Se llama al inicio de cada turno. Siempre consume la acción pendiente (vale una sola vez).
# Devuelve el texto a decir si el mensaje era un sí/no explícito; None si hay que seguir normal.
def resolver(usuario_id: str, texto: str) -> str | None:
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
