# Versión de prueba de las herramientas de calendario: no llama a Google Calendar real.
# Cuando Herramientas resuelva el OAuth real, estas se reemplazan por las reales
# (mismo nombre, misma firma) en src/herramientas/calendario.py.

# funcion para crear un evento en el calendario
def crear_evento_calendario(titulo: str, inicio: str, fin: str) -> str:
    return f"Evento '{titulo}' creado (falso) entre {inicio} y {fin}"

# funcion para listar eventos en el calendario
def listar_eventos(desde: str, hasta: str) -> list[dict]:
    return [{"titulo": "Reunión de prueba", "inicio": desde, "fin": desde}]
