# Avances de Marcelo (Agente A: prompt y conexión LLM)

**Versión 1.0** · 2026-11-08

Documentación técnica del agente: [`agente.md`](agente.md).

## Estado de las tareas (`docs/etapa1.md`, Grupo Agente, Persona A)

- [x] Prompt base del asistente en `src/agente/prompt.py`.
- [x] Conexión con Groq (`openai/gpt-oss-120b`) y `responder(texto, usuario_id) -> RespuestaAgente` en `src/agente/agente.py`, con el ciclo del agente en CrewAI.
- [x] Herramientas de calendario expuestas al agente (`src/agente/tools.py`) y ahora conectadas al calendario real de Ingrid.
- [x] Confirmación de eventos decidida por el código (`src/agente/confirmacion.py`).
- [ ] Memoria entre turnos: es de Persona B. `usuario_id` ya llega a `responder()` para ese fin.

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
