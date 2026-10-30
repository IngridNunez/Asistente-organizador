# Contratos entre módulos

Cada función es la frontera entre equipos. Mientras un equipo no tenga su
parte lista, los demás usan la versión "falsa" (stub) que vive en el mismo
archivo, para no bloquearse entre sí.

## Voz

```python
def transcribir(audio: bytes) -> str:
    """Recibe audio grabado (bytes, ej. wav) y devuelve el texto reconocido."""

def hablar(texto: str) -> bytes:
    """Recibe texto y devuelve audio (bytes, ej. wav/mp3) listo para reproducir."""
```
Archivo: `src/voz/`

## Agente

```python
def responder(texto: str, usuario_id: str) -> str:
    """Recibe el texto transcrito y el id del usuario (para memoria),
    ejecuta el razonamiento y las herramientas necesarias,
    y devuelve el texto de respuesta final."""
```
Archivo: `src/agente/`

## Herramientas

Cada herramienta que usa el agente sigue la interfaz de "tool" de LangChain:
nombre, descripción y función con entradas/salidas tipadas. Ejemplos:

```python
def crear_evento_calendario(titulo: str, inicio: str, fin: str) -> str:
    """Crea un evento en Google Calendar. Devuelve confirmación o error."""

def listar_eventos(desde: str, hasta: str) -> list[dict]:
    """Devuelve los eventos entre dos fechas (ISO 8601)."""
```
Archivo: `src/herramientas/`

Toda acción sobre el PC (etapa 4) debe ser una función específica y acotada
(no ejecución de comandos libres), ver `docs/seguridad.md`.

## API (FastAPI)

```
POST /conversar
  body: { "audio": <bytes o base64>, "usuario_id": str }
  respuesta: { "texto_respuesta": str, "audio_respuesta": <bytes o base64> }
```
Internamente encadena: `transcribir -> responder -> hablar`.
Archivo: `src/api/`

## Interfaz (cliente, PC o celular)

El cliente solo necesita:
1. Grabar audio al apretar el botón.
2. Mandarlo a la API (`POST /conversar`).
3. Reproducir el audio de respuesta.
4. Si la respuesta implica una acción local (ej. abrir una app), ejecutarla
   usando las funciones de `src/herramientas/` permitidas para el dispositivo.

## Stubs mientras se integra

Cada equipo agrega, en su propio módulo, una versión falsa de lo que todavía
no existe, por ejemplo:

```python
# src/agente/calendario_falso.py
def listar_eventos(desde, hasta):
    return [{"titulo": "Reunión de prueba", "inicio": desde, "fin": desde}]
```

Así el equipo de Agente puede avanzar sin esperar a que OAuth de Google
Calendar esté resuelto, y se reemplaza el stub por la función real cuando
esté lista, sin cambiar la firma.
