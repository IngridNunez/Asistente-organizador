import json

from crewai.tools import tool

# Hoy se importan las versiones "_falso": cuando Herramientas termine las reales
# (src/herramientas/calendario.py), solo cambia este import.
from src.herramientas import calendario_falso as calendario


# Tools que ve el agente. Envuelven las funciones de src/herramientas/ sin cambiar su firma.
@tool("crear_evento_calendario")
def crear_evento_calendario(titulo: str, inicio: str, fin: str) -> str:
    """Crea un evento en el calendario del usuario. Úsala solo después de que el usuario
    confirme título, día y hora. `inicio` y `fin` van en formato ISO 8601, por ejemplo
    2026-11-09T17:00:00."""
    return calendario.crear_evento_calendario(titulo, inicio, fin)


@tool("listar_eventos")
def listar_eventos(desde: str, hasta: str) -> str:
    """Lista los eventos del calendario del usuario entre dos fechas. `desde` y `hasta`
    van en formato ISO 8601, por ejemplo 2026-11-09T00:00:00."""
    return json.dumps(calendario.listar_eventos(desde, hasta), ensure_ascii=False)


TOOLS_AGENTE = [crear_evento_calendario, listar_eventos]
