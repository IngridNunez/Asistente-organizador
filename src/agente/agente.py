def responder(texto: str, usuario_id: str) -> str:
    raise NotImplementedError


def responder_falso(texto: str, usuario_id: str) -> str:
    return f"Recibí: {texto}"
