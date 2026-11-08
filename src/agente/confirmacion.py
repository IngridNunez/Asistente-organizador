import re
import time
import uuid
from dataclasses import dataclass

# Hoy se importa la versión "_falso": cuando Herramientas termine la real, solo cambia este import.
from src.herramientas import calendario_falso as calendario

# Una acción propuesta caduca a los 5 minutos: una confirmación vieja no debe ejecutar nada.
TTL_SEGUNDOS = 300

# Palabras que cuentan como "sí". Si el mensaje trae cualquier otra, NO se ejecuta:
# "sí, pero a las 6" debe tratarse como un pedido nuevo, no como confirmación.
PALABRAS_SI = {
    "si", "sí", "confirmo", "confirmado", "dale", "ok", "okay", "claro", "correcto",
    "perfecto", "adelante", "hazlo", "crealo", "créalo", "confirmalo", "confírmalo",
    "por", "favor", "gracias",
}
PALABRAS_NO = {"no", "cancela", "cancelar", "cancelalo", "cancélalo", "olvidalo", "olvídalo"}


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


# La herramienta del agente llama aquí: NO crea nada, solo deja la propuesta esperando el "sí".
def proponer(usuario_id: str, titulo: str, inicio: str, fin: str) -> str:
    accion = AccionPendiente(uuid.uuid4().hex[:8], titulo, inicio, fin, time.monotonic())
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
    if palabras[0] in PALABRAS_NO:
        return "Listo, no lo creé."
    if len(palabras) <= 5 and all(p in PALABRAS_SI for p in palabras):
        return calendario.crear_evento_calendario(accion.titulo, accion.inicio, accion.fin)
    return None
