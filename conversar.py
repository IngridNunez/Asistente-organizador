"""Cliente de consola para conversar con el agente."""

from src.agente.agente import responder


def main() -> None:
    print("Habla con el agente. Escribe 'salir' para terminar.\n")

    while True:
        texto = input("tú> ").strip()
        if texto.lower() in {"salir", "exit", "q"}:
            break

        respuesta = responder(texto, "consola")
        print(f"sara> {respuesta.texto}")
        if respuesta.confirmacion_pendiente:
            print("      (esperando tu sí o no)")
        print()


if __name__ == "__main__":
    main()
