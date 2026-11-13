# Avances de Marcelo (Agente A: prompt y conexión LLM)

**Versión 1.1** · 2026-11-13

Documentación técnica del agente: [`agente.md`](agente.md).

## Estado de las tareas (`docs/etapa1.md`, Grupo Agente, Persona A)

- [x] Prompt base del asistente en `src/agente/prompt.py`, con la personalidad de Sara (2026-11-13).
- [x] Conexión con Groq (`openai/gpt-oss-120b`) y `responder(texto, usuario_id) -> RespuestaAgente` en `src/agente/agente.py`, con el ciclo del agente en CrewAI.
- [x] Herramientas de calendario expuestas al agente (`src/agente/tools.py`) y ahora conectadas al calendario real de Ingrid.
- [x] Confirmación de eventos decidida por el código (`src/agente/confirmacion.py`).
- [ ] Memoria entre turnos: es de Persona B. `usuario_id` llega a `responder()` desde el token de la API. El saludo exclusivo al inicio depende de esa memoria.

## 2026-11-13

- **Qué hice (paso a paso):**
  - **Paso 1: Personalidad de Sara en el prompt.** `construir_prompt_sistema` define a Sara como calmada, cercana, animada, profesional, resolutiva y proactiva. Trabaja en el contexto del CITT de Duoc UC, sede Viña del Mar, y no se presenta como servicio institucional aprobado.
  - **Paso 2: Identidad y TTS.** Sara escribe "Sara" y no la sigla, para que la voz no deletree. Si preguntan quién es: "Soy Sara, tu Sistema de Agendamiento y Reserva de Actividades."
  - **Paso 3: Franjas de saludo en Python.** `saludo_del_momento(ahora)` usa `ahora.hour` y `America/Santiago`: 00:00–11:59 "Buenos días", 12:00–19:59 "Buenas tardes", 20:00–23:59 "Buenas noches". El prompt no obliga a saludar en cada turno.
  - **Paso 4: Proactividad.** El prompt exige consultar la agenda con `listar_eventos` antes de proponer, avisar de cruces y ofrecer reorganizar una agenda cargada.
  - **Paso 5: Pregunta de confirmación desde el código.** Con propuesta pendiente, `responder()` devuelve `confirmacion.resumen()`, no el texto del modelo. Lo que el usuario oye es lo que se guarda.
  - **Paso 6: Topes de entrada.** `responder()` acota el texto a 2000 caracteres antes de `confirmacion.resolver`. `listar_eventos` rechaza rangos de más de 31 días sin llamar al calendario.
  - **Paso 7: Usuario fijo por instalación.** La API usa `API_USUARIO` como `usuario_id` e ignora el campo del body. Sin `API_AUTH_TOKEN` o sin `API_USUARIO` responde 503.
  - **Paso 8: Docstrings** en las funciones nuevas o cambiadas de `prompt.py`, `confirmacion.py`, `tools.py`, `agente.py`, `api/main.py` y los tests.
  - **Paso 9: Documentación.** Actualicé `agente.md` a la versión 1.1 y esta página.
- **Resultado de las pruebas (2026-11-13):** 92 pasan, 3 fallan. Los 3 fallos son de `tests/test_api.py` y llaman al STT real de Groq (`groq.NotFoundError`). Ya fallaban antes de estos cambios. Las pruebas del agente no usan Groq real.
- **Decisiones y por qué:**
  - Saludo y franja los calcula el código. El modelo no calcula la hora.
  - La pregunta de confirmación sale del código porque el texto del modelo puede no coincidir con lo guardado.
  - El `usuario_id` es fijo por instalación porque el proyecto es de una sola persona. Un mapeo token-usuario era más complejo y no resolvía un caso que hoy no existe.
  - Hallazgos de la auditoría de seguridad del agente: se corrigieron los 4 accionables (usuario desde el token, resumen de confirmación desde código, tope de 31 días en `listar_eventos`, tope de texto antes del resolver). El quinto es informativo (el delimitador `"""` no es frontera) y no requiere cambio.
- **Qué falta o qué me bloquea:**
  - **Saludo exclusivo al inicio.** Depende de la memoria de Persona B.
  - **Validación del LLM real.** Las pruebas del prompt son estructurales. Falta comprobar con Groq real que el modelo sigue el tono, la proactividad y el cierre.
  - **Cambio de contrato de la API.** El `usuario_id` del body se ignora y hay que configurar `API_USUARIO` en cada `.env`. Hay que avisar al equipo.
  - **Estados visuales.** El brief pide cinco estados; `docs/meritxell/personalidad-sara.md` tiene siete (`error` y `cancelado`). Hay que decidir antes de codificarlos.

## 2026-11-07 y 2026-11-08

- **Qué hice (paso a paso):**
  - **Paso 1: Definí `RespuestaAgente`** (`texto`, `accion_local`, `confirmacion_pendiente`) y adapté el stub `responder_falso`.
  - **Paso 2: Escribí el prompt base** y expuse las tools de calendario al agente.
  - **Paso 3: Conecté `responder` con Groq y CrewAI.** Documenté el uso de CrewAI y marqué la tarea.
  - **Paso 4: Preparé el entorno.** Fijé Python 3.12 (`.python-version`, `pytest.ini`), importé `crewai` solo al responder y bajé el ruido de logs cuando Groq falla. Dejé escrito en el README y en `AGENTS.md` que hay que usar Python 3.12 con el venv activo.
  - **Paso 5: Endurecí la seguridad.**
    - La confirmación para crear eventos pasó del prompt al código (`confirmacion.py`).
    - La API exige token y acota la entrada de `/conversar`.
    - Quité la neutralización de comillas triples: no era una frontera de seguridad real.
    - La API valida el token antes de leer el body y acepta saltos de línea.
  - **Paso 6: Ordené dependencias y tipos.** Fijé versiones, restauré `langchain` y `langchain-openai` (otros grupos las usan), acoté el tipo del resultado de `kickoff()` y apliqué el formato automático.
  - **Paso 7: Reforcé el prompt contra el voseo.** El modelo respondía con "tenés" o "querés"; ahora el prompt pide tuteo neutro con ejemplos.
  - **Paso 8: Integré el calendario real de Ingrid** con un merge de `feature/calendario`. `confirmacion.py` usa `calendario` en vez de `calendario_falso`.
  - **Paso 9: Agregué docstrings** a los cuatro módulos de `src/agente/`.
  - **Paso 10: Verifiqué.** Probé el agente por consola con el calendario real (la evidencia está en `docs/ingrid/ingrid.md`).
  - **Paso 11: Auditoría del agente y arreglos** (commit `e393f6f`).
    - El LLM tiene `timeout` de 30 s y el agente un tope de 5 pasos.
    - `proponer_evento_calendario` devuelve lo guardado y el prompt pide la duración.
    - `listar_eventos` devuelve `Error: ...` en vez de lanzar la excepción.
    - 5 tests nuevos (caída de Groq, claves faltantes, tools). Pasan los 69 tests del proyecto.
- **Decisiones y por qué:**
  - Un sí o un no lo resuelve el código, no el modelo. Un modelo engañado por un título de evento o por el texto del usuario no puede crear nada.
  - La respuesta de confirmación es estricta: "sí, pero a las 6" se trata como pedido nuevo, no como confirmación.
  - Las propuestas caducan a los 5 minutos y valen una sola vez.
  - El estado de confirmación vive en memoria porque, en las etapas 1 a 4, todo corre en un proceso.
  - El agente usa CrewAI y no LangChain, aunque `langchain` sigue en las dependencias.
- **Qué falta o qué me bloquea:**
  - **Probar la duración en vivo.** El prompt ya la pide, pero mi `GROQ_API_KEY` está vencida (`401 expired_api_key`). Falta renovarla y probar por consola.
  - **Cuelgue de OAuth en `calendario.py` (archivo de Ingrid).** Sin token guardado, `run_local_server` espera sin límite y bloquea la petición. `_credenciales()` debería lanzar un error pidiendo autorizar. Falta avisarle.
  - **`/conversar` usa `responder_falso`.** Cambiar a `responder` cuando STT y TTS reales estén listos, con un test de la API.
  - **Estado en memoria.** Con varios procesos o el celular remoto, `_PENDIENTES` debe moverse a un almacén compartido (etapa 5).
  - **Borrar eventos desde el agente.** Hoy el contrato solo tiene crear y listar. Es una acción delicada: exige confirmación y generalizar `confirmacion.py`. Falta hablarlo con Ingrid y actualizar `docs/contratos.md`.
