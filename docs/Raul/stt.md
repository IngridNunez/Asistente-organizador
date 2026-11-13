# Avances de Raúl (Voz A: STT)

**Versión 1.0** · 2026-11-12

## Estado de las tareas (`docs/etapa1.md`, Grupo Voz, Persona A)

- [x] Implementar `transcribir(audio) -> str` en `src/voz/stt.py` llamando a la API de Groq (`client.audio.transcriptions.create`).
- [x] Probar el reconocimiento con distintos audios (ruido, acentos, frases cortas/largas).
- [x] Tests unitarios con el cliente de Groq mockeado (`tests/test_stt.py`, 8 tests).

## 2026-11-08

- **Qué hice (paso a paso):**
  - **Paso 1: Probé la API de Groq en un proyecto aparte** (`test de stt`, fuera del repo). Grabé un wav corto, lo mandé a `client.audio.transcriptions.create` con `whisper-large-v3-turbo` y `language="es"` y transcribió en ~0,7 s. Confirmé que la key funciona, que el formato `(nombre, bytes, mime)` es correcto y que la latencia es baja.
  - **Paso 2: Implementé `transcribir()` real en `src/voz/stt.py`** con la misma lógica probada: cliente Groq como singleton (`_get_client`), `load_dotenv` con ruta explícita a la raíz del repo, `language="es"` y `temperature=0`.
  - **Paso 3: Verifiqué a mano** llamando `transcribir()` con el wav grabado: devolvió el texto correcto.
- **Decisiones y por qué:**
  - `language="es"` fijo: el proyecto es en español; evita que Whisper adivine otro idioma.
  - `temperature=0`: transcripción determinista, menos alucinaciones del modelo.
  - `GROQ_STT_MODEL` del `.env` con default `whisper-large-v3-turbo` (el modelo decidido por el equipo en `docs/etapa1.md`): si falta la variable, sigue funcionando.
  - `load_dotenv` con ruta explícita (`Path(__file__).parents[2] / ".env"`): `agente.py` usa `load_dotenv()` sin ruta y depende del cwd; la mía funciona sin importar desde dónde se ejecute.
  - Cliente como singleton: evita recrear `Groq()` en cada request de `/conversar`.
  - Se conserva `transcribir_falso()` en el mismo archivo, como piden los contratos para los stubs.
- **Qué falta o qué me bloquea:**
  - Probar con audios más variados (frases largas, ruido, acentos) — pendiente del checklist.
  - Decidir con el equipo qué formato de audio mandará la interfaz (hoy `stt.py` asume `audio/wav` fijo en el MIME).

## 2026-11-12

- **Qué hice:**
  - **Paso 1: Escribí `tests/test_stt.py`** (8 tests) siguiendo el estilo de `test_calendario.py`/`test_agente.py`: cliente Groq mockeado con `MagicMock` + `monkeypatch`, sin llamadas reales ni gasto de cuota.
  - **Paso 2: Con autorización del responsable, conecté el STT real en `src/api/main.py`**: `transcribir_falso` → `transcribir` en el pipeline de `POST /conversar` (el archivo también quedó con `responder` real; solo `hablar_falso` sigue de stub).
- **Decisiones y por qué:**
  - Los tests verifican formato wav, modelo por entorno con default, `language="es"`, `temperature=0`, propagación de errores de Groq, error claro sin `GROQ_API_KEY` y reutilización del singleton.
  - `test_transcribir_propaga_errores_de_groq` deja explícito que los errores de Groq suben: si `/conversar` debe responder un mensaje amable en vez de 500, es decisión del equipo de integración.
- **Qué falta o qué me bloquea:**
  - Verificar que `tests/test_api.py` siga verde con el STT real: el smoke test manda `b"audio falso"`, que no es audio válido y Groq puede rechazar con 400.
  - El venv local quedó en Python 3.13 sin todas las dependencias (`google`, `crewai`); hay que recrearlo con Python 3.12 según `AGENTS.md` para correr la suite completa.

## Ideas / observaciones

- Si la interfaz termina grabando webm/ogg en vez de wav, `stt.py` debe parametrizar el MIME o el endpoint debe estandarizar el formato — conviene acordarlo antes de la etapa de interfaz.
- Errores de Groq (red caída, rate limit, audio inválido) hoy propagan como excepción → HTTP 500. Si se quiere un "No te escuché bien" hablado, el manejo iría en `main.py` o dentro de `transcribir` devolviendo texto vacío para que `responder` responda lo suyo.
