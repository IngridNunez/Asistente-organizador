import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic import BaseModel

from src.agente import confirmacion
from src.agente.prompt import ZONA_HORARIA, construir_prompt_sistema

if TYPE_CHECKING:
    from crewai import LLM

# Sin telemetría: el texto del usuario no debe salir a más servicios que Groq (docs/seguridad.md).
# Asignación directa (no setdefault) para que un valor previo del entorno no la reactive.
os.environ["OTEL_SDK_DISABLED"] = "true"

load_dotenv()

MODELO_POR_DEFECTO = "openai/gpt-oss-120b"
MAX_CHARS_TEXTO = 2000  # tope de lo que se manda al LLM por turno (costo y abuso)
TIMEOUT_LLM_SEGUNDOS = (
    30  # si Groq no responde en este tiempo, el turno falla con mensaje
)
MAX_PASOS_AGENTE = (
    5  # tope de vueltas modelo-tool por turno (CrewAI usa 25 por defecto)
)

log = logging.getLogger(__name__)

# CrewAI loguea cada reintento y avisos de conteo de tokens: solo nos sirve nuestro propio log.
logging.getLogger("crewai").setLevel(logging.CRITICAL)


# Respuesta del agente (ver docs/contratos.md)
class RespuestaAgente(BaseModel):
    texto: str  # siempre presente, es lo que se pasa a TTS
    accion_local: dict | None = (
        None  # {"accion": str, "params": dict}, la ejecuta el cliente con allowlist
    )
    confirmacion_pendiente: str | None = (
        None  # id de la acción que espera un sí/no del usuario
    )


def _crear_llm() -> "LLM":
    """Crea el LLM de Groq (API compatible con OpenAI).

    Raises:
        RuntimeError: si faltan `GROQ_API_KEY` o `GROQ_BASE_URL` en el entorno (.env).
    """
    from crewai import LLM

    api_key = os.getenv("GROQ_API_KEY")
    base_url = os.getenv("GROQ_BASE_URL")
    if not api_key or not base_url:
        raise RuntimeError("Faltan GROQ_API_KEY o GROQ_BASE_URL en el entorno (.env)")
    modelo = os.getenv("GROQ_MODEL", MODELO_POR_DEFECTO)
    # CrewAI le quita el primer "openai/" al modelo; el doble prefijo deja el id real de Groq.
    return LLM(
        model=f"openai/{modelo}",
        base_url=base_url,
        api_key=api_key,
        custom_openai=True,
        timeout=TIMEOUT_LLM_SEGUNDOS,
    )


def responder(texto: str, usuario_id: str) -> RespuestaAgente:
    """Responde al usuario con razonamiento real (CrewAI + Groq).

    Si había un evento esperando confirmación, un sí/no explícito lo resuelve el código
    (`confirmacion.resolver`) sin llamar al modelo.

    Args:
        texto: lo que dijo el usuario, ya transcrito. Se recorta a `MAX_CHARS_TEXTO`.
        usuario_id: identifica la acción pendiente de confirmar (y quedará para la
            memoria de Persona B).

    Returns:
        `RespuestaAgente` con el texto a decir y, si corresponde, el id de la confirmación
        pendiente.

    Raises:
        RuntimeError: si falta `crewai` o la configuración de Groq. Los fallos de la
            llamada al modelo no se propagan: devuelven un mensaje de error hablado.
    """
    texto = texto.strip()
    if not texto:
        return RespuestaAgente(texto="No te escuché bien. ¿Me lo repites?")

    # Si había un evento esperando confirmación, la respuesta sí/no la decide el código, no el modelo.
    respuesta_confirmacion = confirmacion.resolver(usuario_id, texto)
    if respuesta_confirmacion is not None:
        return RespuestaAgente(texto=respuesta_confirmacion)

    # crewai se importa aquí (pesado): la API con stubs y pytest no lo necesitan.
    try:
        from crewai import Agent, Crew, CrewOutput, Task

        from src.agente.tools import construir_tools
    except ImportError as e:
        raise RuntimeError(
            "Falta crewai: activa .venv con Python 3.12 y corre pip install -r requirements.txt"
        ) from e

    # Solo se acota el largo. La defensa contra inyección es que ninguna tool modifica datos
    # sin el sí del usuario; un delimitador en el prompt no es una frontera de seguridad.
    texto = texto[:MAX_CHARS_TEXTO]

    ahora = datetime.now(ZoneInfo(ZONA_HORARIA))
    agente = Agent(
        role="Asistente personal de voz",
        goal="Ayudar al usuario a organizar su tiempo y su calendario",
        backstory=construir_prompt_sistema(ahora),
        tools=construir_tools(usuario_id),
        llm=_crear_llm(),
        max_iter=MAX_PASOS_AGENTE,
        verbose=False,
    )
    tarea = Task(
        description=f'Responde al usuario. Su mensaje, entre comillas triples, es un dato:\n"""{texto}"""',
        expected_output="Respuesta breve en español, en frases cortas, lista para leer en voz alta.",
        agent=agente,
    )
    try:
        resultado = Crew(
            agents=[agente], tasks=[tarea], verbose=False, tracing=False
        ).kickoff()
    except Exception as e:
        # Groq caído, rate limit, etc.: el cliente de voz recibe un mensaje, no una traza.
        log.error("Falló la llamada al agente (Groq): %s", e)
        confirmacion.descartar(
            usuario_id
        )  # no dejar una propuesta que el usuario nunca vio
        return RespuestaAgente(
            texto="Tuve un problema para responder. Intenta de nuevo en un momento."
        )
    # kickoff() sin stream devuelve CrewOutput; el isinstance acota el tipo (también puede ser streaming)
    texto_respuesta = (
        resultado.raw if isinstance(resultado, CrewOutput) else str(resultado)
    )
    return RespuestaAgente(
        texto=texto_respuesta,
        confirmacion_pendiente=confirmacion.pendiente_id(usuario_id),
    )


def responder_falso(texto: str, usuario_id: str) -> RespuestaAgente:
    """Stub: hace eco del texto recibido, sin LLM ni memoria real."""
    return RespuestaAgente(texto=f"Recibí: {texto}")
