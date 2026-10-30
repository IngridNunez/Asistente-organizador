def crear_evento_calendario(titulo: str, inicio: str, fin: str) -> str:
    return f"Evento '{titulo}' creado (falso) entre {inicio} y {fin}"


def listar_eventos(desde: str, hasta: str) -> list[dict]:
    return [{"titulo": "Reunión de prueba", "inicio": desde, "fin": desde}]
