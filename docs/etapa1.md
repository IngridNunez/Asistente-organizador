# Etapa 1: trabajo real en paralelo por grupo

Gracias al patrón de contratos y stubs (`docs/contratos.md`), ningún grupo
necesita esperar a que otro termine: cada uno implementa su parte real desde
ya, usando las versiones "_falso" de lo que todavía no existe en los demás
módulos. Esta etapa reúne las tareas reales de cada grupo para partir todos
en paralelo, no solo el loop de voz. Dentro de cada grupo, las tareas también
están divididas por persona para que ninguna de las dos se bloquee esperando
a la otra.

## Decisiones ya tomadas

- **STT:** se utilizará **Whisper vía Groq**, modelo
  `GROQ_STT_MODEL=whisper-large-v3-turbo` (ver `.env.example` /
  `requirements.txt`). Decidido porque reutiliza la misma API key del LLM y
  no depende del hardware de cada laptop. Cada integrante tiene su propia
  cuenta gratuita de Groq: durante el desarrollo, cada uno usa su propia
  `GROQ_API_KEY` en su `.env` local, para no pegar en los límites de rate
  compartiendo una sola key. Con cuál key corre el servidor para la demo
  final se decide más adelante.

## Grupo Voz

**Persona A — STT**

- [ ] Implementar `transcribir(audio) -> str` en `src/voz/stt.py` llamando a
      la API de Groq (`client.audio.transcriptions.create`).
- [ ] Probar el reconocimiento con distintos audios (ruido, acentos, frases
      cortas/largas).

**Persona B — TTS**

- [ ] Elegir motor de TTS (edge-tts o Piper).
- [ ] Implementar `hablar(texto) -> bytes` en `src/voz/tts.py`.
- [ ] Probar calidad y latencia de la voz generada.

**Juntas:**

- [ ] Probar el ciclo completo: grabar -> transcribir -> hablar -> escuchar.

**Referencia (repo `Ingeniería de Soluciones con IA`):**

- `RA1/IL1.1/1-groq_model_api.ipynb` — llamadas directas a la API de Groq
  (formato de respuesta, latencia) antes de decidir el STT.
- `RA1/IL1.1/3-langchain_streaming.ipynb` — streaming de respuestas, útil si
  quieren que el TTS empiece a hablar antes de que el LLM termine de generar.

## Grupo Agente

**Persona A — Prompt y conexión LLM**

- [ ] Armar el prompt base del asistente (tono, qué puede y no puede hacer).
- [ ] Implementar la conexión LangChain + Groq (`openai/gpt-oss-120b`) y el
      esqueleto de `responder(texto, usuario_id) -> RespuestaAgente` en
      `src/agente/agente.py` (ver `docs/contratos.md`), llamando a
      `crear_evento_calendario_falso` / `listar_eventos` mientras
      Herramientas no tenga lista la versión real.

**Persona B — Memoria**

- [ ] Agregar memoria de conversación simple (por `usuario_id`).
- [ ] Probar que mantiene contexto entre 2-3 mensajes seguidos.

**Juntas:**

- [ ] Decidir en qué casos `responder()` debe devolver `accion_local` o
      `confirmacion_pendiente` (ver `docs/contratos.md`).

**Referencia:**

- `RA1/IL1.1/2-langchain_model_api.ipynb` — conexión base de LangChain con el
  modelo que van a usar en `responder()`.
- `RA1/IL1.2/*` (zero-shot, few-shot, chain-of-thought, advanced-techniques) —
  aplica directo a armar el prompt base.
- `RA2/IL2.2/1-memory-agent.ipynb` y `2-memory-agent-advanced.ipynb` — para la
  memoria de conversación simple.
- *Adelanto opcional:* `RA1/IL1.3/*` (basic-rag, text-chunking,
  embeddings-simple-rag, vector-rag) — no se implementa en esta etapa, pero
  conviene revisarlos ahora si la memoria de largo plazo (etapa 3) va a usar
  retrieval en vez de una lista plana: afecta cómo guardan los mensajes desde
  ya.

## Grupo Herramientas

**Antes de separarse, acordar entre las dos personas:**

- [ ] El mecanismo de confirmación a usar (`confirmacion_pendiente` de
      `RespuestaAgente`, ver `docs/contratos.md`) — ambas tracks lo van a
      necesitar, no debería inventarse dos veces.
- [ ] El criterio de allowlist (lista explícita de acciones permitidas, nunca
      texto libre del LLM) para aplicarlo igual en ambos módulos.
- [ ] Trabajar en sub-secciones separadas de `docs/seguridad.md` y
      `docs/contratos.md` (una por persona) para no chocar en los merges.

**Persona A — Calendario (etapa 2)**

- [ ] Resolver el flujo de OAuth real de Google Calendar (credenciales,
      scopes, dónde queda guardado el token — documentarlo en
      `docs/seguridad.md`).
- [ ] Implementar `crear_evento_calendario` y `listar_eventos` reales en
      `src/herramientas/calendario.py`, respetando exactamente la firma de
      `docs/contratos.md` (no hace falta esperar a que Agente las use).
- [ ] Avisar al Grupo Agente antes de reemplazar `calendario_falso.py` por la
      integración real, para que el cambio sea de una línea (mismo nombre de
      función, mismo contrato).

**Persona B — Acceso al PC (etapa 4, adelantado)**

- [ ] Definir la allowlist de acciones permitidas sobre el PC (qué funciones
      existen, qué parámetros aceptan).
- [ ] Implementar esas funciones en `src/herramientas/pc.py`, acotadas y sin
      `eval`/`exec`/`subprocess` con texto que venga del LLM.
- [ ] Documentar en `docs/seguridad.md` los riesgos identificados, aunque la
      integración completa con el agente se active recién en etapa 4.

**Referencia:**

- `RA2/IL2.1/2-agent-function-calling.ipynb` — cómo se conecta una tool al
  agente (aplica a ambas, Calendario y PC).
- `RA1/IL1.3/4-vector-rag.ipynb` — si más adelante se decide construir una
  herramienta `consultar_documentos` (RAG como tool), este es el ejemplo base
  de base de datos vectorial.

## Interfaz

- [ ] Decidir interfaz definitiva (web/Gradio-Streamlit, Telegram o ambas)
      y actualizar `src/interfaz/`.
- [ ] Construir el botón de "grabar" y la reproducción de la respuesta,
      consumiendo `POST /conversar` de la API.

**Referencia:**

- `RA2/IL2.4/` (plantillas de documentación y diagramas de arquitectura) —
  para dejar registrada la decisión final (web vs. Telegram).

## Integración

- [ ] Levantar la API (`src/api/main.py`) con `uvicorn` y probar
      `POST /conversar` end to end con los stubs.
- [ ] Reemplazar los stubs por las implementaciones reales a medida que
      cada grupo termine, sin cambiar las firmas de `docs/contratos.md`.
- [ ] Armar el tablero en GitHub Projects con estas tareas como issues.

**Referencia:**

- `RA2/IL2.4/best-practices.md` y `architecture-guide.md` — para mantener
  consistencia en cómo se documentan los módulos a medida que se integran.

---

> Todas las rutas de "Referencia" son relativas a
> `Track/Ingenier-a-de-Soluciones-con-Inteligencia-Artificial/` del repo del
> curso, no a este repositorio.
