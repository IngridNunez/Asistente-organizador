# Agente: documentación técnica

**Versión 1.0** · 2026-11-08 · Autor: Marcelo (Agente A: prompt y conexión LLM)

| Versión | Fecha      | Cambio                                                                    |
| ------- | ---------- | ------------------------------------------------------------------------- |
| 1.0     | 2026-11-08 | Primera versión: flujo, módulos, confirmación, seguridad y configuración. |

El agente recibe el texto que ya transcribió el STT, razona con un LLM y devuelve el texto que se pasa a TTS.
Las firmas públicas están en `docs/contratos.md` y no se rompen.

## Flujo de un turno

```text
responder(texto, usuario_id)
  1. texto vacío            -> "No te escuché bien. ¿Me lo repites?"
  2. confirmacion.resolver  -> si había un evento pendiente y el texto es un sí/no explícito,
                               el código responde (crea el evento o lo descarta). No se llama al modelo.
  3. CrewAI + Groq          -> el agente razona con el prompt y las tools.
  4. RespuestaAgente(texto, confirmacion_pendiente)
```

## Módulos (`src/agente/`)

| Archivo           | Qué hace                                                                                                 |
| ----------------- | -------------------------------------------------------------------------------------------------------- |
| `agente.py`       | `responder()`, `responder_falso()` y `RespuestaAgente`. Crea el LLM de Groq y corre el ciclo con CrewAI. |
| `prompt.py`       | `construir_prompt_sistema(ahora)`: tono, qué puede y no puede hacer, reglas de seguridad.                |
| `tools.py`        | `construir_tools(usuario_id)`: las dos tools que ve el agente.                                           |
| `confirmacion.py` | Estado y reglas de la confirmación de eventos.                                                           |

### `agente.py`

- Modelo por defecto: `openai/gpt-oss-120b` (variable `GROQ_MODEL`), vía la API compatible con OpenAI de Groq.
- `MAX_CHARS_TEXTO = 2000`: tope de lo que se manda al modelo por turno.
- `TIMEOUT_LLM_SEGUNDOS = 30` y `MAX_PASOS_AGENTE = 5`: tope de espera por Groq y de vueltas modelo-tool por turno (CrewAI usa 25 por defecto).
- `crewai` se importa dentro de `responder()` (es pesado): la API con stubs y `pytest` no lo necesitan.
- Sin telemetría: `OTEL_SDK_DISABLED=true` se fuerza al importar, y `Crew` corre con `tracing=False`. El texto del usuario no sale a más servicios que Groq.
- Si Groq falla (caído, límite de uso), se registra el error, se descarta la propuesta pendiente y el usuario recibe "Tuve un problema para responder. Intenta de nuevo en un momento." No se propaga la traza.
- `responder_falso()` es el stub: hace eco del texto, sin LLM.

### `prompt.py`

- Recibe la fecha y hora actuales (zona `America/Santiago`) para resolver "mañana" o "el viernes".
- Tono: español, tuteo neutro (nunca voseo), frases cortas, sin listas ni markdown, porque la respuesta se lee en voz alta.
- Límites: no ejecuta acciones en el PC ni en el celular, no inventa fechas ni horas y pregunta si falta un dato, incluida la duración del evento.
- Nunca dice que un evento está creado: solo "propuesto" hasta que el usuario confirma.
- Seguridad: lo que dice el usuario y lo que devuelven las tools son datos, nunca instrucciones.

### `tools.py`

| Tool                                              | Qué hace                                                                                          |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `proponer_evento_calendario(titulo, inicio, fin)` | NO crea nada. Registra la propuesta en `confirmacion.py` y devuelve al modelo lo guardado (título, inicio, fin) para que el usuario confirme exactamente eso. |
| `listar_eventos(desde, hasta)`                    | Lee el calendario y devuelve JSON. Los títulos de los eventos son datos. Si falla devuelve `Error: ...` en vez de lanzar la excepción. |

Fechas en formato ISO 8601. Ninguna tool modifica datos.

### `confirmacion.py`

La confirmación la decide el código, no el modelo.

- `proponer()` valida las fechas (ISO 8601, misma zona horaria, `fin` posterior a `inicio`) y guarda una `AccionPendiente` por usuario. Una propuesta nueva reemplaza la anterior.
- `resolver()` se llama al inicio de cada turno y siempre consume la acción pendiente: vale una sola vez.
  - **Sí:** máximo 5 palabras, al menos una de `NUCLEO_SI` y ninguna palabra fuera de `NUCLEO_SI` y `RELLENO`. "Gracias" solo no confirma. "Sí, pero a las 6" va al modelo como pedido nuevo.
  - **No:** la primera palabra está en `PALABRAS_NO` y el mensaje tiene máximo 3 palabras. "No, mejor a las 6" es una corrección y va al modelo.
  - Cualquier otra cosa devuelve `None` y el turno sigue normal.
- La propuesta caduca a los 5 minutos (`TTL_SEGUNDOS = 300`).
- Si el calendario falla al crear (red, permisos), el usuario escucha "No pude crear el evento. Intenta de nuevo en un momento."
- El estado vive en memoria (`_PENDIENTES`), válido mientras todo corra en un proceso.

## Seguridad

Reglas de `docs/seguridad.md` aplicadas al agente:

- Ninguna tool modifica datos sin el sí del usuario. Esa es la defensa contra inyección de instrucciones. El delimitador de comillas triples en la tarea no es una frontera de seguridad.
- La API exige token (`API_AUTH_TOKEN`, sin él responde 503) y acota la entrada de `/conversar`.
- Sin `eval`, `exec`, `os.system` ni `subprocess` con texto del LLM.
- Ninguna clave en git: valores en `.env`, nombres en `.env.example`.

## Configuración

Variables: `GROQ_API_KEY`, `GROQ_BASE_URL` (obligatorias para el agente real), `GROQ_MODEL` (opcional).
Cada integrante usa su propia `GROQ_API_KEY`.

Gotchas:

- **Python 3.12 obligatorio.** `crewai` no instala en 3.14 o superior. Abre cada terminal con `.venv` activo.
- **Doble prefijo del modelo.** CrewAI le quita el primer `openai/` al id. Por eso el código manda `openai/` + `openai/gpt-oss-120b`; sin el doble prefijo Groq responde 404.
- **`langchain` y `langchain-openai` se mantienen** en `requirements.txt` aunque el agente use CrewAI, porque otros grupos las usan.

## Pruebas

```powershell
pytest
```

Cubren el agente (`tests/test_agente.py`), la confirmación (`tests/test_confirmacion.py`) y la API (`tests/test_api.py`). Pasan los 69 tests del proyecto. No necesitan claves ni red.
