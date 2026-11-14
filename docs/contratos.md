# Contratos entre módulos

Cada función es la frontera entre equipos. Mientras un equipo no tenga su
parte lista, los demás usan la versión "falsa" (stub) que vive en el mismo
archivo, para no bloquearse entre sí.

## Etapas del proyecto

1. Voz en el PC (grabar, transcribir, responder, hablar) — ver `docs/etapa1.md`.
2. Calendario.
3. Memoria y planificación ("organiza mi semana").
4. Acceso controlado al PC.
5. Celular.

Las firmas de abajo son válidas desde la etapa 1 y no deberían romperse al
avanzar de etapa (ver nota de `responder()` sobre qué cambia en la etapa 5).

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
class RespuestaAgente(BaseModel):
    texto: str                                  # siempre presente, para TTS
    accion_local: dict | None = None            # {"accion": str, "params": dict} si hay que
                                                 # ejecutar algo en el dispositivo (allowlist aparte)
    confirmacion_pendiente: str | None = None    # id de la acción que espera un sí/no explícito
                                                 # del usuario antes de ejecutarse (ver seguridad.md)

def responder(texto: str, usuario_id: str) -> RespuestaAgente:
    """Recibe el texto transcrito y el id del usuario (para memoria),
    ejecuta el razonamiento y las herramientas necesarias,
    y devuelve texto + (opcional) acción local o confirmación pendiente."""
```

Archivo: `src/agente/`

Internamente `responder()` usa CrewAI (Agent, Task, Crew) con Groq como LLM, y
expone las herramientas de calendario con `@tool` de `crewai.tools` en
`src/agente/tools.py`. La firma de `responder()` no cambia por esto.

Crear un evento requiere confirmación y la impone el código, no el modelo: la
tool `proponer_evento_calendario` no crea nada, solo deja la propuesta en
`src/agente/confirmacion.py` y `responder()` devuelve su id en
`confirmacion_pendiente`. En el turno siguiente, un "sí" explícito del usuario
ejecuta el evento; un "no", cualquier otro mensaje o 5 minutos de espera lo
descartan. `accion_local` sale siempre en `None` por ahora.

El agente nunca ejecuta directamente una acción sobre el PC: solo la propone en
`accion_local`. Quien la ejecuta de verdad es la capa de herramientas/cliente,
que aplica la allowlist (ver `docs/seguridad.md`).

**Nota sobre dónde corre esto (etapas 1-4):** hasta que entre el celular
(etapa 5), agente, API y cliente corren en el mismo PC/proceso. Esto simplifica
la confirmación: el estado de "acción pendiente de confirmar" puede vivir en
memoria del propio agente (ej. un dict `usuario_id -> acción pendiente`), sin
necesidad de correlacionar across dispositivos. Cuando el celular se vuelva un
cliente remoto real, este estado va a tener que moverse a donde el agente
(servidor) pueda verlo sin depender de que el mismo proceso siga vivo.

### Memoria de conversación

`responder()` usa la memoria de `src/agente/memoria.py`: guarda los últimos 3
turnos de cada `usuario_id` y los incluye en el siguiente turno. Hoy vive en la
RAM del proceso, así que se pierde al reiniciar.

```python
def guardar_turno(usuario_id: str, usuario_texto: str, asistente_texto: str) -> None:
    """Guarda un turno; si hay más de 3, descarta el más antiguo."""

def obtener_historial(usuario_id: str) -> list[TurnoConversacion]:
    """Devuelve una copia de los turnos guardados (máximo 3)."""

def obtener_historial_formateado(usuario_id: str) -> str:
    """Devuelve el historial como texto para el prompt; vacío si no hay."""

def cantidad_conversaciones(usuario_id: str) -> int:
    """Devuelve cuántos turnos hay guardados (0 a 3)."""

def limpiar_memoria(usuario_id: str | None = None) -> None:
    """Borra la memoria de un usuario, o de todos si no se indica."""
```

## Herramientas

Las funciones de `src/herramientas/` son funciones normales, con entradas y
salidas tipadas. El agente las expone al modelo con `@tool` de CrewAI en
`src/agente/tools.py`. Ejemplos:

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

```py
POST /conversar
  header: Authorization: Bearer <API_AUTH_TOKEN>
  body: { "audio_base64": str }           # el usuario sale de API_USUARIO; un "usuario_id" en el body se ignora
  respuesta: { "texto_respuesta": str, "audio_base64": str }
```

Internamente encadena: `transcribir -> responder -> hablar`. El `texto` de
`RespuestaAgente` es lo que se pasa a `hablar()`; si `responder` devuelve
`accion_local` o `confirmacion_pendiente`, por ahora (etapas 1-4, agente local)
se resuelven en el mismo proceso antes de responder.
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
# src/herramientas/calendario_falso.py
def listar_eventos(desde, hasta):
    return [{"titulo": "Reunión de prueba", "inicio": desde, "fin": desde}]
```

Así el equipo de Agente puede avanzar sin esperar a que OAuth de Google
Calendar esté resuelto, y se reemplaza el stub por la función real cuando
esté lista, sin cambiar la firma.
