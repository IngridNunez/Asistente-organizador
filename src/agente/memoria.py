"""Módulo de memoria de conversación para el agente.

Permite almacenar y recuperar hasta 3 conversaciones (turnos de interacción)
por cada usuario_id en memoria del proceso (etapas 1-4).
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging

log = logging.getLogger(__name__)

# Límite estricto de conversaciones (turnos) a retener por usuario
MAX_CONVERSACIONES = 3


@dataclass
class TurnoConversacion:
    """Representa un turno completo de conversación entre el usuario y el asistente."""

    usuario: str
    asistente: str
    fecha: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        """Devuelve la representación en diccionario del turno."""
        return asdict(self)


# Estado en memoria (usuario_id -> lista de hasta MAX_CONVERSACIONES turnos)
_HISTORIAL: dict[str, list[TurnoConversacion]] = {}


def guardar_turno(usuario_id: str, usuario_texto: str, asistente_texto: str) -> None:
    """Guarda un turno completo de interacción para un usuario.

    Si el historial supera MAX_CONVERSACIONES (3), descarta automáticamente
    el turno más antiguo (comportamiento de ventana deslizante FIFO).

    Args:
        usuario_id: Identificador único del usuario.
        usuario_texto: Mensaje o petición expresada por el usuario.
        asistente_texto: Respuesta generada por el asistente.
    """
    usuario_id = usuario_id.strip() if usuario_id else ""
    if not usuario_id:
        log.warning("Intento de guardar turno con usuario_id vacío.")
        return

    if usuario_id not in _HISTORIAL:
        _HISTORIAL[usuario_id] = []

    nuevo_turno = TurnoConversacion(
        usuario=usuario_texto.strip() if usuario_texto else "",
        asistente=asistente_texto.strip() if asistente_texto else "",
    )
    _HISTORIAL[usuario_id].append(nuevo_turno)

    # Mantener únicamente las últimas MAX_CONVERSACIONES
    if len(_HISTORIAL[usuario_id]) > MAX_CONVERSACIONES:
        _HISTORIAL[usuario_id] = _HISTORIAL[usuario_id][-MAX_CONVERSACIONES:]


def obtener_historial(usuario_id: str) -> list[TurnoConversacion]:
    """Devuelve una copia de la lista de turnos (hasta 3) de un usuario.

    Args:
        usuario_id: Identificador del usuario.

    Returns:
        Lista de instancias de TurnoConversacion (máximo 3).
    """
    usuario_id = usuario_id.strip() if usuario_id else ""
    return list(_HISTORIAL.get(usuario_id, []))


def obtener_historial_formateado(usuario_id: str) -> str:
    """Devuelve el historial formateado como texto listo para inyectar en prompts.

    Args:
        usuario_id: Identificador del usuario.

    Returns:
        Cadena con formato 'Usuario: ...\\nAsistente: ...' o vacía si no hay historial.
    """
    turnos = obtener_historial(usuario_id)
    if not turnos:
        return ""

    lineas: list[str] = []
    for turno in turnos:
        lineas.append(f"Usuario: {turno.usuario}")
        lineas.append(f"Asistente: {turno.asistente}")
    return "\n".join(lineas)


def cantidad_conversaciones(usuario_id: str) -> int:
    """Devuelve la cantidad de turnos de conversación almacenados para el usuario.

    Args:
        usuario_id: Identificador del usuario.

    Returns:
        Entero entre 0 y MAX_CONVERSACIONES (3).
    """
    usuario_id = usuario_id.strip() if usuario_id else ""
    return len(_HISTORIAL.get(usuario_id, []))


def limpiar_memoria(usuario_id: str | None = None) -> None:
    """Limpia la memoria de conversaciones.

    Args:
        usuario_id: Si se proporciona, limpia solo el historial de ese usuario.
            Si es None, limpia el historial completo de todos los usuarios.
    """
    if usuario_id is None:
        _HISTORIAL.clear()
    else:
        usuario_id = usuario_id.strip() if usuario_id else ""
        _HISTORIAL.pop(usuario_id, None)
