import dataclasses
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Único punto donde el agente toca el calendario (tools.py lo reutiliza desde aquí).
# Usa el calendario real (Google Calendar). Para volver al stub: calendario_falso as calendario.
from src.herramientas import calendario

log = logging.getLogger(__name__)

# Una acción propuesta caduca a los 5 minutos: una confirmación vieja no debe ejecutar nada.
TTL_SEGUNDOS = 300
MENSAJE_VENCIDA = "La propuesta venció. Dime de nuevo qué agendar."
MENSAJE_CAMBIO = "Esa propuesta ya cambió. Revisa la propuesta actual antes de confirmar."

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


@dataclass(frozen=True)
class AccionPendiente:
    id: str
    titulo: str
    inicio: str
    fin: str
    creada: float
    # Avisos calculados por código (conflictos con la agenda). Tupla: inmutable.
    advertencias: tuple[str, ...] = ()
    # Propuesta nueva que espera autorización para reemplazar esta. Ver `proponer()`.
    reemplazo: "AccionPendiente | None" = None
    # Turno del modelo que la propuso. Permite quitar solo lo de un intento fallido.
    turno: str = ""


@dataclass(frozen=True)
class ConsultaAgenda:
    """Consulta de agenda exitosa de un turno. Solo vale para ese usuario y ese turno."""

    usuario_id: str
    turno_id: str
    desde: datetime
    hasta: datetime
    intervalos: tuple[tuple[datetime, datetime], ...]


# Estado en memoria del agente (etapas 1-4, todo corre en un proceso): usuario_id -> acción pendiente.
# Con varios procesos o el celular remoto esto debe moverse a un almacén compartido.
_PENDIENTES: dict[str, AccionPendiente] = {}
# Protege las transiciones de `_PENDIENTES`. La llamada al calendario se hace fuera de este lock.
_LOCK = threading.Lock()


def tipo_de_error(e: BaseException) -> str:
    """Tipo de excepción y código HTTP, sin el mensaje: los mensajes pueden traer datos del usuario o credenciales."""
    codigo = getattr(e, "status_code", None)
    return type(e).__name__ + (f" HTTP {codigo}" if codigo else "")


def _palabras(texto: str) -> list[str]:
    return re.findall(r"\w+", texto.lower())


def interpretar_si_no(texto: str) -> str | None:
    """Clasifica el mensaje como "si", "no" o None (cualquier otra cosa). Función pura."""
    palabras = _palabras(texto)
    if not palabras:
        return None
    if palabras[0] in PALABRAS_NO and len(palabras) <= MAX_PALABRAS_NO:
        return "no"
    if (
        len(palabras) <= MAX_PALABRAS_SI
        and any(p in NUCLEO_SI for p in palabras)
        and all(p in NUCLEO_SI or p in RELLENO for p in palabras)
    ):
        return "si"
    return None


def _vigente(accion: AccionPendiente, ahora: float) -> bool:
    return ahora - accion.creada <= TTL_SEGUNDOS


def _purgar_vencidas() -> None:
    """Borra las propuestas vencidas de todos los usuarios, para que el dict no crezca sin límite."""
    ahora = time.monotonic()
    for usuario, accion in list(_PENDIENTES.items()):
        if not _vigente(accion, ahora):
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


def validar_propuesta(titulo: str, inicio: str, fin: str) -> str:
    """Valida una propuesta con las mismas reglas que `calendario.crear_evento_calendario`.

    Así una propuesta válida aquí no falla después del "sí" por el calendario.

    Returns:
        El título sin espacios en los extremos, que es el que se guardará y se creará.

    Raises:
        ValueError: si el título está vacío o supera `calendario.MAX_CHARS_TITULO`, o si las
            fechas no son válidas (ver `_validar_fechas`).
    """
    titulo = titulo.strip()
    if not titulo:
        raise ValueError("el título no puede estar vacío")
    if len(titulo) > calendario.MAX_CHARS_TITULO:
        raise ValueError(
            f"el título es demasiado largo (máximo {calendario.MAX_CHARS_TITULO} caracteres)"
        )
    _validar_fechas(inicio, fin)
    return titulo


def instante(valor: str) -> datetime:
    """Convierte ISO 8601 en instante con zona. Sin zona usa `calendario.ZONA_HORARIA`, igual que calendario."""
    fecha = datetime.fromisoformat(valor)
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=ZoneInfo(calendario.ZONA_HORARIA))
    return fecha


def hay_solapamiento(a_ini: datetime, a_fin: datetime, b_ini: datetime, b_fin: datetime) -> bool:
    """Intervalos semiabiertos: un evento que termina a la hora en que empieza otro no es conflicto."""
    return a_ini < b_fin and b_ini < a_fin


def consulta_que_cubre(
    consultas: list[ConsultaAgenda], usuario_id: str, turno_id: str, inicio: str, fin: str
) -> ConsultaAgenda | None:
    """Primera consulta del mismo usuario y turno que contiene por completo [inicio, fin]."""
    ini, f = instante(inicio), instante(fin)
    for consulta in consultas:
        if (
            consulta.usuario_id == usuario_id
            and consulta.turno_id == turno_id
            and consulta.desde <= ini
            and f <= consulta.hasta
        ):
            return consulta
    return None


def advertencias_de(consulta: ConsultaAgenda, inicio: str, fin: str) -> tuple[str, ...]:
    """Avisos de conflicto con la agenda consultada. Los genera código, no el modelo."""
    ini, f = instante(inicio), instante(fin)
    zona = ZoneInfo(calendario.ZONA_HORARIA)
    avisos = []
    for e_ini, e_fin in consulta.intervalos:
        if not hay_solapamiento(ini, f, e_ini, e_fin):
            continue
        if e_fin - e_ini >= timedelta(days=1):
            avisos.append("Coincide con un evento de día completo.")
        else:
            avisos.append(
                f"Coincide con otra actividad de {e_ini.astimezone(zona):%H:%M} "
                f"a {e_fin.astimezone(zona):%H:%M}."
            )
    return tuple(avisos)


def _texto_propuesta(accion: AccionPendiente) -> str:
    desde = datetime.fromisoformat(accion.inicio)
    hasta = datetime.fromisoformat(accion.fin)
    base = f"Puedo registrar {accion.titulo} el {desde:%d/%m} de {desde:%H:%M} a {hasta:%H:%M}."
    avisos = " ".join(accion.advertencias)
    return " ".join(p for p in (base, avisos, "¿La confirmo?") if p)


def _texto_reemplazo(actual: AccionPendiente, nueva: AccionPendiente) -> str:
    """Pregunta de la etapa 1: autoriza el reemplazo, pero no crea nada."""
    desde = datetime.fromisoformat(nueva.inicio)
    hasta = datetime.fromisoformat(nueva.fin)
    return (
        f"Ya tengo pendiente {actual.titulo}. ¿Lo reemplazo por {nueva.titulo} "
        f"el {desde:%d/%m} de {desde:%H:%M} a {hasta:%H:%M}?"
    )


def _id_esperado(accion: AccionPendiente) -> str:
    """Id de lo que el usuario debe responder ahora: el reemplazo si existe, o la propuesta."""
    return accion.reemplazo.id if accion.reemplazo else accion.id


def proponer(
    usuario_id: str,
    titulo: str,
    inicio: str,
    fin: str,
    advertencias: tuple[str, ...] = (),
    turno: str = "",
) -> str:
    """Registra una propuesta de evento. La tool del agente llama aquí, después de validar la consulta.

    NO crea nada. Si ya hay una propuesta vigente, la nueva queda como reemplazo pendiente:
    el usuario debe autorizar el cambio y luego confirmar la propuesta nueva.

    Args:
        turno: turno del modelo que propone; lo usa `descartar_turno` si ese intento falla.

    Returns:
        El id de lo que el usuario debe responder ahora (ver `pendiente_id`).

    Raises:
        ValueError: si el título o las fechas no son válidas (ver `validar_propuesta`).
    """
    titulo = validar_propuesta(titulo, inicio, fin)
    nueva = AccionPendiente(
        uuid.uuid4().hex[:8],
        titulo,
        inicio,
        fin,
        time.monotonic(),
        tuple(advertencias),
        turno=turno,
    )
    with _LOCK:
        _purgar_vencidas()
        actual = _PENDIENTES.get(usuario_id)
        if actual is not None:
            _PENDIENTES[usuario_id] = dataclasses.replace(actual, reemplazo=nueva)
        else:
            _PENDIENTES[usuario_id] = nueva
    return nueva.id


def resumen(usuario_id: str) -> str | None:
    """Texto armado desde los datos guardados, no desde lo que dijo el modelo."""
    with _LOCK:
        accion = _PENDIENTES.get(usuario_id)
        if accion is None or not _vigente(accion, time.monotonic()):
            return None
        if accion.reemplazo is not None:
            return _texto_reemplazo(accion, accion.reemplazo)
        return _texto_propuesta(accion)


def descartar(usuario_id: str) -> None:
    """Elimina la acción pendiente del usuario, si existe."""
    with _LOCK:
        _PENDIENTES.pop(usuario_id, None)


def descartar_turno(usuario_id: str, turno: str) -> None:
    """Quita lo que propuso el turno `turno` (intento fallido). Lo de otros turnos se conserva.

    Si el turno había creado la propuesta principal, la sustituye el reemplazo ajeno, si existe.
    """
    with _LOCK:
        accion = _PENDIENTES.get(usuario_id)
        if accion is None:
            return
        if accion.reemplazo is not None and accion.reemplazo.turno == turno:
            accion = dataclasses.replace(accion, reemplazo=None)
        if accion.turno != turno:
            _PENDIENTES[usuario_id] = accion
        elif accion.reemplazo is None:
            _PENDIENTES.pop(usuario_id, None)
        else:
            _PENDIENTES[usuario_id] = accion.reemplazo


def cerrar_turno(usuario_id: str, visto: str | None) -> None:
    """Fin de turno sin error: si el usuario dijo otra cosa y el modelo no propuso reemplazo, la propuesta vista se consume.

    Así "sí, pero a las 6" o cualquier texto libre no deja una propuesta viva sin revisar.
    """
    with _LOCK:
        accion = _PENDIENTES.get(usuario_id)
        if accion is not None and visto is not None and accion.id == visto and accion.reemplazo is None:
            _PENDIENTES.pop(usuario_id, None)


def pendiente_id(usuario_id: str) -> str | None:
    """Id de lo que el usuario debe responder: el reemplazo si existe, o la propuesta. None si no hay vigente."""
    with _LOCK:
        accion = _PENDIENTES.get(usuario_id)
        if accion is None or not _vigente(accion, time.monotonic()):
            return None
        return _id_esperado(accion)


def _transicion(
    usuario_id: str, texto: str, visto: str | None, ahora: float
) -> tuple[str | None, AccionPendiente | None]:
    """Decide la respuesta a un mensaje y muta el estado. Debe llamarse con `_LOCK` tomado.

    Returns:
        (texto a decir, acción a ejecutar). La acción solo se devuelve en el "sí" de ejecución.
    """
    accion = _PENDIENTES.get(usuario_id)
    intencion = interpretar_si_no(texto)
    if accion is None:
        # Había algo pendiente al empezar el turno y ya no: otra solicitud lo consumió.
        return (MENSAJE_CAMBIO if visto and intencion else None), None
    if visto is not None and intencion is not None and visto != _id_esperado(accion):
        return MENSAJE_CAMBIO, None

    if not _vigente(accion, ahora):
        _PENDIENTES.pop(usuario_id, None)
        return (MENSAJE_VENCIDA if intencion == "si" else None), None

    if accion.reemplazo is not None:
        # Etapa 1: solo se autoriza el reemplazo. Nada se crea aquí.
        candidata = accion.reemplazo
        if not _vigente(candidata, ahora):
            _PENDIENTES[usuario_id] = dataclasses.replace(accion, reemplazo=None)
            return (MENSAJE_VENCIDA if intencion == "si" else None), None
        if intencion == "si":
            nueva = dataclasses.replace(
                candidata, id=uuid.uuid4().hex[:8], reemplazo=None
            )
            _PENDIENTES[usuario_id] = nueva
            return _texto_propuesta(nueva), None
        if intencion == "no":
            _PENDIENTES[usuario_id] = dataclasses.replace(accion, reemplazo=None)
            return "Listo, mantengo la propuesta anterior.", None
        # Otro mensaje descarta el reemplazo y conserva la propuesta actual.
        _PENDIENTES[usuario_id] = dataclasses.replace(accion, reemplazo=None)
        return None, None

    # Etapa 2 o propuesta sin reemplazo: el "sí" autoriza la ejecución.
    # Otro mensaje deja la propuesta para el turno del modelo: si ese turno no propone nada, `cerrar_turno` la descarta.
    if intencion == "si":
        _PENDIENTES.pop(usuario_id, None)
        return None, accion
    if intencion == "no":
        _PENDIENTES.pop(usuario_id, None)
        return "Listo, no lo creé.", None
    return None, None


def resolver(usuario_id: str, texto: str, visto: str | None = None) -> str | None:
    """Resuelve la confirmación pendiente del usuario. Se llama al inicio de cada turno.

    Un "sí" o "no" explícito se resuelve aquí; cualquier otro mensaje descarta la propuesta
    (o el reemplazo) pendiente y devuelve None para que siga el modelo.

    Args:
        usuario_id: dueño de la propuesta.
        texto: lo que dijo el usuario.
        visto: id de lo que el usuario debía responder al empezar el turno (ver `pendiente_id`).
            Si la propuesta cambió mientras tanto, no se ejecuta nada.

    Returns:
        El texto a decir si el mensaje era un sí/no explícito; None si hay que seguir normal.
    """
    # Se resuelve al llamar (no como valor por defecto) para que los tests puedan parchear el calendario.
    ejecutar = calendario.crear_evento_calendario
    with _LOCK:
        respuesta, accion = _transicion(usuario_id, texto, visto, time.monotonic())
    if accion is None:
        return respuesta
    try:
        # Fuera del lock: una llamada lenta a Google no bloquea a otros usuarios.
        return ejecutar(accion.titulo, accion.inicio, accion.fin)
    except Exception as e:
        # El calendario real puede fallar (red, permisos): se avisa, no se tumba la petición.
        log.error("Falló la creación del evento: %s", tipo_de_error(e))
        return "No pude crear el evento. Intenta de nuevo en un momento."
