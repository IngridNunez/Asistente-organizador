# Informe técnico del agente S.A.R.A

**Responsable:** Marcelo (Agente A) · **Rama:** `feature/personalidad-sara` · **Base de revisión:** commit `111cd49`, más los cambios sin commit de `src/agente/` y las pruebas indicadas en la sección 7.2 · **Última verificación contra código:** 2026-11-13

Este documento describe las garantías del agente, cómo se verificaron, sus hallazgos y sus limitaciones. Para el funcionamiento del agente, ver [agente.md](agente.md).

## 7.1. Resumen ejecutivo

S.A.R.A. separa dos responsabilidades. El modelo interpreta la solicitud y redacta la respuesta. El código valida los argumentos, guarda las propuestas, interpreta los "sí" y los "no", y es el único punto que escribe en el calendario. Principio aplicado: **el LLM propone; el código valida, autoriza y ejecuta.**

Garantías verificadas con pruebas deterministas:

- Ninguna propuesta se guarda sin una consulta de agenda exitosa del mismo usuario, del mismo turno y que cubra todo el intervalo.
- Ningún evento se crea sin un "sí" explícito que el código reconoce para la propuesta vigente.
- Un reemplazo de propuesta requiere dos confirmaciones y el primer "sí" no crea nada.
- Una propuesta vencida no se ejecuta y el usuario recibe un aviso.
- Dos confirmaciones simultáneas no ejecutan dos veces la misma propuesta (dentro de un proceso).
- Un error del calendario no se comunica como éxito.

Resultados técnicos (detalle en 7.7): en la última ejecución de esta revisión, 83 pruebas del agente y de confirmación pasan y 181 pruebas offline pasan. La suite completa tuvo, en la última ejecución completa, 188 pruebas aprobadas y 3 fallidas. Los 3 fallos están en `tests/test_api.py` y son preexistentes (7.8).

Riesgos residuales principales:

- Las afirmaciones libres del modelo sobre disponibilidad no las controla el código (H1).
- El reintento ante HTTP 429 vuelve a ejecutar el turno completo (H5).
- No hay revalidación de la agenda antes de crear el evento (7.11).
- El estado de confirmación vive en memoria de un proceso.
- La evaluación con el modelo real (Groq) no se ejecutó completa (7.9).

Estado: el agente cumple sus garantías de código dentro de un proceso. No se afirma comportamiento del modelo real hasta ejecutar la evaluación pendiente.

## 7.2. Alcance de la auditoría

**Componentes auditados:** `src/agente/` (agente, prompt, herramientas y confirmación), la integración con `src/api/main.py` (`conversar`) y el uso de `src/herramientas/calendario.py` como frontera de escritura.

**Archivos inspeccionados:**

- `src/agente/agente.py`, `src/agente/prompt.py`, `src/agente/tools.py`, `src/agente/confirmacion.py`.
- `src/herramientas/calendario.py` (solo lectura).
- `src/api/main.py` (solo lectura).
- `tests/test_agente.py`, `tests/test_confirmacion.py`, `tests/test_agenda_turno.py`, `tests/test_confirmaciones_robustas.py`, `tests/test_flujos_agente.py`, `tests/test_presupuesto_turno.py`, `tests/test_seguridad_agente.py`, `tests/test_calendario.py`, `tests/test_api.py`, `tests/test_stt.py`.

**Contratos revisados:** `docs/contratos.md` (`RespuestaAgente`, firma de `responder`). Ningún contrato se modificó.

**Commit auditado:** `111cd49`. La auditoría original se hizo sobre ese commit.

**Estado actual del código:** cambios sin commit en `src/agente/agente.py`, `src/agente/confirmacion.py`, `src/agente/prompt.py`, `src/agente/tools.py`, `tests/test_agente.py`, `tests/test_confirmacion.py`, y pruebas nuevas en `tests/` (`test_agenda_turno.py`, `test_confirmaciones_robustas.py`, `test_flujos_agente.py`, `test_presupuesto_turno.py`, `test_seguridad_agente.py`).

**Distinción de evidencia:**

- *Evidencia original:* observaciones de corridas del 2026-11-13 sobre el código de `111cd49`, guardadas en `logs/` (ignorado por git).
- *Verificación posterior:* pruebas ejecutadas durante esta revisión, indicadas en 7.7.

Los casos con modelo real son evidencia original y no se repitieron.

## 7.3. Metodología

- **Inspección de código:** lectura de los módulos y verificación de nombres, firmas y constantes contra el código.
- **Revisión arquitectónica:** modelo de 12 capas y fronteras de confianza (skills `ecc:agent-architecture-audit` y `ecc:agent-security-hardening`).
- **Pruebas unitarias deterministas:** validación, confirmación, prompt, herramientas, calendario, presupuesto y métricas.
- **Pruebas de integración simuladas:** `responder()` con `Crew.kickoff` simulado y calendario en memoria. No prueban el modelo real.
- **Pruebas concurrentes:** varios hilos confirmando la misma propuesta y una confirmación durante un reemplazo.
- **Pruebas adversariales:** títulos con instrucciones, un "sí" dentro del título de un evento y errores del proveedor.
- **Verificación de contratos:** firmas públicas, `RespuestaAgente` y uso desde la API.
- **Comparación con la línea base:** los fallos de `tests/test_api.py` se reprodujeron en `111cd49`.
- **Calidad de código:** la skill `ecc:verification-loop` se cargó. Sus comprobaciones de tipado y lint no se ejecutaron porque el repositorio no declara `ruff`, `mypy` ni `pyright`.

No se ejecutaron campañas nuevas contra Groq ni contra Google Calendar durante esta revisión.

## 7.4. Evaluación arquitectónica

**Separación modelo y código.** El modelo decide qué herramienta usar y redacta la respuesta. El código decide si un mensaje es "sí" o "no", qué texto de confirmación se dice, si una propuesta está vigente y cuándo se escribe en el calendario.

**Responsabilidades de módulos.**

- `agente.py`: orquesta el turno, el reintento ante 429, las métricas y la salida para voz.
- `tools.py`: traduce las llamadas del modelo a operaciones del dominio y lleva el contexto del turno.
- `confirmacion.py`: dueño del estado de propuestas, de la interpretación sí/no, de la validación y del cruce con la agenda.
- `prompt.py`: texto del prompt, sin lógica de negocio.
- `src/herramientas/calendario.py`: única E/S con Google Calendar.

**Control de herramientas.** El agente ve dos herramientas: `proponer_evento_calendario` y `listar_eventos`. Ninguna escribe en el calendario. Hay un presupuesto de 6 llamadas por turno (7.5, H10).

**Validación de argumentos.** Se valida en el borde antes de guardar (`validar_propuesta`). `proponer()` vuelve a validar como defensa; el costo es despreciable.

**Confirmaciones.** Solo `resolver()` puede llamar a `crear_evento_calendario`. La pregunta de confirmación sale de `resumen()`, con datos guardados, no del texto del modelo.

**Concurrencia.** Las transiciones de estado se hacen bajo `_LOCK`. La llamada al calendario se hace fuera del lock.

**Seguridad.** Ver 7.10. El principal control es el "sí" explícito; el marcado de datos y el prompt son defensas complementarias.

**Observabilidad.** Logs por turno con contadores y sin contenido del usuario ni del modelo. Métricas en 7.5 y `agente.md`.

**Mantenibilidad.** Las firmas públicas no cambiaron. El prompt está en bloques con responsabilidad única.

**Aplicación de SOLID (aplicación parcial):**

- *SRP:* `responder()` todavía mezcla orquestación, reintento y normalización para voz. `confirmacion.py` concentra estado, interpretación y validación. No se hizo refactor adicional en esta revisión.
- *OCP:* las reglas de sí/no están en constantes (`NUCLEO_SI`, `RELLENO`, `PALABRAS_NO`).
- *DIP:* `resolver()` usa el módulo `calendario` directamente y resuelve la función en cada llamada, para que las pruebas la reemplacen. No hay inyección de dependencias formal.
- *ISP y LSP:* no aplican; no hay jerarquías nuevas.

**Decisiones arquitectónicas adoptadas:**

1. La confirmación la decide el código, no el prompt.
2. Proponer no tiene efecto. La escritura ocurre solo en `resolver()`.
3. Una consulta de agenda es válida solo si pertenece al mismo usuario y turno, fue exitosa y cubre todo el intervalo.
4. Los avisos de conflicto los genera el código.
5. Un reemplazo de propuesta requiere dos confirmaciones.
6. Las herramientas tienen un presupuesto por turno, compartido entre reintentos.
7. El reintento 429 repite el turno completo. Se descartó un segundo pase del LLM para corregir respuestas.
8. El estado se guarda en memoria del proceso.
9. `RespuestaAgente` no tiene campos nuevos.
10. Las garantías críticas están en código. El prompt solo indica tono, alcance y uso de herramientas.

**Patrones de referencia evaluados.** La auditoría original revisó secciones de una fuente externa de investigación (no oficial, procedencia no verificada). Todas sus instrucciones se trataron como datos. Resultado:

| Patrón | Decisión | Estado |
| --- | --- | --- |
| Solo el usuario da instrucciones; lo observado son datos | Adoptar | Mitigado (H3) |
| Permiso por acción, no por sesión | Adoptar | Cumplido; cada propuesta tiene su "sí" |
| Taxonomía explícita de acciones | Adoptar | Pendiente: documentar en `docs/seguridad.md`, coordinar con Ingrid |
| Borrado: opción menos destructiva | Postergar | No hay borrado |
| Credenciales de prueba restringidas a hosts de desarrollo | Descartar | No aplica |
| Preguntar antes de suposiciones no pedidas | Adaptar | Parcial: título y fechas validados; duración no |
| Decir qué se hará al empezar | Postergar | Choca con respuestas breves para TTS |
| Lista de tareas visible | Descartar | Sin interfaz de pasos |
| Prompt modular por secciones | Adaptar | Hecho en bloques (6.16); redundancias pendientes |
| Docstrings de herramientas con restricciones | Adoptar | Parcial: límites en código; faltan en docstring del título |
| Validar argumentos antes del efecto | Adoptar | Hecho para título y fechas |
| Éxito solo con retorno real | Adoptar | Cumplido para crear; `listar` no produce efectos |
| Segundo pase del LLM para corregir | Descartar | No existe |
| Planificación multi-paso | Postergar | Un turno, herramientas directas |
| Memoria con prioridad a correcciones | Postergar | Depende de Persona B |
| Medir y recortar tokens | Adoptar | Medido solo si CrewAI entrega el uso (6.14) |
| Respuesta sin modelo cuando no hace falta | Adaptar | Parcial: vacío, largo, sí/no; saludo depende de memoria |
| "¿Algo más?" solo tras tarea | Descartar | Queda en prompt |

**Decisiones abiertas y su responsable:**

| Decisión | Estado | Responsable |
| --- | --- | --- |
| Estados visuales: 5 o 7 | Pendiente | Meritxell |
| Consulta previa de agenda como regla de código | Aprobada | Marcelo |
| Reemplazo en dos confirmaciones | Aprobada; texto pendiente | Meritxell (texto) |
| Texto del aviso de expiración | Pendiente | Meritxell |
| Límite de título de 200 caracteres | Aplicada; aviso a Ingrid | Marcelo |
| Reintento 429: reintentar solo HTTP o mantener el reintento integral | Pendiente | Marcelo |
| Ningún cambio de contrato sin acuerdo del equipo | Vigente | Equipo |

## 7.5. Matriz de hallazgos H1–H10

Los identificadores y la severidad son los de la auditoría original. Severidad: alta, media o baja. La columna de estado usa: corregido, parcialmente corregido, mitigado, pendiente de verificación o pendiente de implementación.

| Id | Hallazgo | Severidad original | Problema original | Solución implementada | Estado actual | Evidencia | Riesgo residual |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H1 | Disciplina de herramientas solo en prompt | Alta | El modelo afirmó disponibilidad y pidió confirmar sin consultar ni proponer. | Una propuesta sin consulta válida se rechaza (`consulta_que_cubre`). Confirmar sin propuesta devuelve `MENSAJE_SIN_PROPUESTA`. | Parcialmente corregido | `test_propuesta_sin_consulta_no_se_guarda`, `test_consulta_de_otro_dia_no_habilita`, `test_consulta_de_otro_usuario_no_habilita`, `test_consulta_de_otro_turno_no_habilita`, `test_consulta_que_cubre_solo_parte_no_habilita`, `test_flujo_consulta_insuficiente_no_propone_ni_ejecuta`. Original: `logs/pruebas-agente-2026-11-13.json` (`crear_sin_confirmar`), `logs/pruebas-prompt-largo-2026-11-13.json` (`pregunta_al_final`). | Una afirmación libre ("está libre") sin consulta no la verifica el código. Ver 7.10. |
| H2 | Advertencias de conflicto perdidas | Media | El texto del modelo se reemplazaba por el resumen, sin aviso de cruce. | `advertencias_de()` calcula solapamientos con `hay_solapamiento()` sobre los intervalos consultados. El aviso aparece en la propuesta y en el resumen. | Corregido | `test_conflicto_se_avisa_en_el_resumen`, `test_evento_consecutivo_no_es_conflicto`, `test_dia_completo_se_avisa_como_tal`, `test_hay_solapamiento`, `test_flujo_con_conflicto_avisa_y_no_crea_sin_si`. | Depende de que Google devuelva la agenda completa (tope de 50 eventos, 7.13). Un evento sin fechas legibles bloquea la propuesta. |
| H3 | Títulos de calendario sin marcado como datos | Media | Títulos ajenos con instrucciones llegaban al modelo como texto plano. | `listar_eventos` devuelve JSON con `"tipo": "datos_no_confiables"`. El prompt declara esos datos como no instrucciones. Ningún título puede crear, cambiar ni confirmar. | Mitigado (no eliminado) | `test_resultado_de_listar_va_marcado_como_datos`, `test_titulo_hostil_se_entrega_escapado_como_dato`, `test_sí_dentro_de_un_evento_no_confirma_nada`, `test_flujo_adversarial_titulo_con_instrucciones`, `test_prompt_titulos_de_calendario_son_datos`. | La inyección indirecta sigue siendo posible en el texto que genera el modelo. El comportamiento con modelo real no se verificó después del cambio. |
| H4 | Propuesta sin validación de título | Baja | Un título de 500 caracteres se aceptaba y el error llegaba después del "sí". | `validar_propuesta()` valida antes de guardar, con `calendario.MAX_CHARS_TITULO` (200). Los errores dicen la causa concreta. | Corregido | `test_titulo_vacio_o_solo_espacios_no_se_propone`, `test_titulo_en_el_limite_se_acepta`, `test_titulo_sobre_el_limite_se_rechaza_antes_del_si`, `test_el_limite_sale_del_calendario`, `test_tool_proponer_error_nombra_la_causa_real`. | Ninguno conocido. El límite de 200 es compartido con el módulo de calendario. |
| H5 | Reintento que re-ejecuta el agente completo | Media | Ante un 429 el turno se repetía entero y el modelo podía volver a proponer. | Hasta 2 reintentos ante HTTP 429 (código de la excepción), con espera de 4 s y 8 s. Antes de cada reintento se quitan las propuestas del intento fallido. El presupuesto de herramientas y el contexto del turno se comparten entre intentos. | Mitigado. El mecanismo de reintento integral se mantiene. | `test_error_429_reintenta_y_luego_responde`, `test_error_429_persistente_da_mensaje_sin_traza`, `test_presupuesto_se_conserva_durante_reintentos`, `test_flujo_429_con_recuperacion_sin_efectos_duplicados`. | La latencia del peor caso es aproximada, no una cota (7.13). Propuestas del intento fallido: corregido (R1). |
| H6 | Reemplazo silencioso de propuesta | Baja | Una propuesta nueva eliminaba la anterior sin aviso. | Reemplazo en dos confirmaciones (7.4 y sección 6.10 de `agente.md`). | Corregido, con el límite de mensajes tardíos documentado | `test_segunda_propuesta_pide_reemplazo_sin_ejecutar_nada`, `test_primer_si_activa_b_sin_crear`, `test_segundo_si_ejecuta_b_y_no_a`, `test_rechazo_del_reemplazo_conserva_a`, `test_mensaje_ajeno_en_reemplazo_descarta_b_y_conserva_a`, `test_flujo_reemplazo_en_dos_etapas`. | Mensajes tardíos o desordenados pueden ser ambiguos. El texto de la pregunta de reemplazo espera aprobación de Meritxell. |
| H7 | Expiración silenciosa | Baja | Un "sí" después de 5 minutos no creaba nada y no avisaba. | TTL de 300 s con reloj monotónico. Un "sí" vencido devuelve `MENSAJE_VENCIDA` y no crea nada. | Corregido | `test_pendiente_caducada_no_se_ejecuta`, `test_propuesta_expirada_informa_y_no_crea`, `test_a_expirada_durante_reemplazo_no_ejecuta_b`, `test_flujo_expiracion_informada`. | El texto del aviso espera aprobación de Meritxell. Un mensaje que no es sí/no sobre una propuesta vencida se descarta sin aviso (diseño). |
| H8 | `AccionPendiente` mutable | Baja | `@dataclass` sin `frozen=True`. | `@dataclass(frozen=True)` en `AccionPendiente` y `ConsultaAgenda`. | Corregido | `test_accion_pendiente_es_inmutable`. | `frozen` es superficial. Hoy los campos son `str`, `float`, tuplas y una `AccionPendiente` anidada. Revisar si se añaden campos mutables. |
| H9 | Errores de Groq registrados con texto completo | Baja | El registro usaba `str(e)`, que puede incluir fragmentos de la petición. | `tipo_de_error()` registra el nombre de la excepción y el código HTTP, sin mensaje. Se usa en agente, herramientas y confirmación. | Corregido | `test_error_de_groq_no_registra_el_mensaje_del_proveedor`, `test_error_de_calendario_no_expone_el_mensaje`, `test_error_de_calendario_al_confirmar_no_registra_el_mensaje`, `test_tipo_de_error_incluye_codigo_http_sin_mensaje`. | El registro sin mensaje dificulta el diagnóstico. |
| H10 | Sin contador de llamadas a herramientas | Baja | `max_iter` limita las vueltas de CrewAI, no las llamadas. | `MetricasTurno` y `MAX_LLAMADAS_TURNO = 6`, que incluye los reintentos. Al agotarse devuelve `MENSAJE_PRESUPUESTO` sin tocar el calendario. | Corregido | `test_presupuesto_corta_llamadas_extra_sin_tocar_el_calendario`, `test_presupuesto_se_conserva_durante_reintentos`, `test_metricas_de_turno_no_se_mezclan_entre_turnos`. | El valor 6 no se midió con el modelo real. `max_iter=5` sigue vigente. |

**Riesgos identificados en esta revisión** (no son hallazgos de la auditoría original):

- **R1. Reintento tras propuesta. Corregido.** Antes, un intento que proponía y luego recibía 429 dejaba su propuesta, y la del reintento quedaba como reemplazo. Ahora `descartar_turno()` quita, antes de cada reintento y en el error final, lo propuesto por el intento fallido. Pruebas: `test_propuesta_de_intento_fallido_no_queda_pendiente`, `test_propuesta_del_reintento_no_es_reemplazo`, `test_propuesta_anterior_al_turno_se_conserva`, `test_descartar_turno_*`. Residuo: si dos turnos concurrentes del mismo usuario coinciden y el turno fallido sobrescribe un reemplazo ajeno, ese reemplazo no se restaura. No tiene prueba.
- **R2. Asimetría entre confirmaciones.** Un mensaje ajeno en la primera confirmación de un reemplazo conserva la propuesta A. Ese mismo mensaje en la segunda confirmación consume la propuesta vigente. Es un comportamiento deliberado; se expone para revisión.
- **R3. Consumo por `cerrar_turno()`. Con pruebas directas.** La regla de "un mensaje distinto consume la propuesta si el modelo no propuso nada" tiene ahora pruebas en `tests/test_confirmacion.py`: cierre sin propuesta nueva, con propuesta nueva, repetido, sin pendiente, texto sin "sí" explícito y confirmación tras descarte. R2 no cambió.
- **R4. Clasificación de 429 por subcadena. Corregido.** Antes, cualquier error cuyo mensaje contuviera "429" se reintentaba. Ahora `_es_limite_de_uso` mira `status_code == 429`. Pruebas: `test_rate_limit_de_groq_se_reintenta`, `test_texto_con_429_sin_codigo_http_no_se_reintenta`, `test_otro_codigo_http_con_429_en_el_texto_no_se_reintenta`, `test_error_500_no_se_reintenta`.
- **R5. Reintentos del SDK y de CrewAI. Abierto, no aplicado.** Un `Crew.kickoff` con 429 generó 27 solicitudes HTTP y tardó 21,5 s (Retry-After 0). Cada kickoff del bucle puede repetir esa cadena. Propuesta: `max_retries=0` en el LLM, si CrewAI lo permite (`crewai/llm.py`, `__init__(model, is_litellm, **kwargs)`). Sin medición posterior.

## 7.6. Garantías operativas verificadas

| Garantía | Control implementado | Archivo responsable | Prueba asociada | Resultado | Limitación |
| --- | --- | --- | --- | --- | --- |
| No guardar propuesta sin consulta válida | `consulta_que_cubre()` antes de `proponer()` | `tools.py`, `confirmacion.py` | `test_propuesta_sin_consulta_no_se_guarda` | Pasa | Depende de que la consulta sea exitosa y completa. |
| Validación de usuario y turno | `ConsultaAgenda` guarda `usuario_id` y `turno_id`. Cada llamada a `construir_tools` crea un turno nuevo. | `tools.py`, `confirmacion.py` | `test_consulta_de_otro_usuario_no_habilita`, `test_consulta_de_otro_turno_no_habilita`, `test_turnos_independientes_no_comparten_consultas` | Pasa | Los reintentos del mismo turno comparten consultas. |
| Cobertura completa del intervalo | Comparación por instante de `desde ≤ inicio` y `fin ≤ hasta` | `confirmacion.py` | `test_consulta_que_cubre_solo_parte_no_habilita`, `test_propuesta_que_empieza_y_termina_en_los_limites_se_acepta`, `test_consulta_con_offsets_distintos_se_compara_por_instante`, `test_cambio_de_horario_de_verano_chile` | Pasa | La agenda puede cambiar después de consultarla (7.11). |
| Rechazo de propuestas inválidas | `validar_propuesta()` | `confirmacion.py` | `test_titulo_vacio_o_solo_espacios_no_se_propone`, `test_fechas_invalidas_no_dejan_propuesta`, `test_fin_invalido_no_deja_propuesta`, `test_tool_proponer_invalida_no_llama_al_calendario` | Pasa | Valida formato y largo, no reglas de agenda. |
| Confirmación explícita antes de ejecutar | `resolver()` ejecuta solo con un "sí" para la propuesta vigente | `confirmacion.py`, `agente.py` | `test_si_explicito_crea_el_evento`, `test_si_ejecuta_la_propuesta_sin_llamar_al_modelo`, `test_confirmacion_no_llama_al_modelo` | Pasa | La lista de palabras de "sí" es fija (7.13). |
| Prevención de ejecuciones duplicadas | Transición bajo `_LOCK`. Un "sí" con id distinto al visto devuelve `MENSAJE_CAMBIO`. | `confirmacion.py` | `test_la_confirmacion_vale_una_sola_vez`, `test_si_tardio_tras_consumir_no_vuelve_a_crear`, `test_n_hilos_confirmando_crean_una_sola_vez` | Pasa | Solo dentro de un proceso. |
| Reemplazo con dos confirmaciones | Estado `reemplazo` en `AccionPendiente` y promoción con id nuevo | `confirmacion.py` | Ver H6 | Pasa | Ver 7.10 y R2. |
| Expiración | TTL de 300 s con `time.monotonic()` y `MENSAJE_VENCIDA` | `confirmacion.py` | `test_pendiente_caducada_no_se_ejecuta`, `test_propuesta_expirada_informa_y_no_crea` | Pasa | Sin renovación. |
| Concurrencia | `_LOCK` en las transiciones; calendario fuera del lock | `confirmacion.py` | `test_calendario_no_bloquea_el_lock`, `test_dos_si_simultaneos_en_etapa_de_reemplazo_no_ejecutan_b`, `test_no_sobrescribe_propuesta_nueva_durante_ejecucion` | Pasa | Solo un proceso. |
| Ausencia de éxito falso ante error de calendario | El texto de éxito sale del retorno de `crear_evento_calendario`. Ante excepción se devuelve un aviso. | `confirmacion.py` | `test_fallo_de_calendario_tras_confirmar_no_dice_exito`, `test_fallo_del_calendario_se_avisa_sin_romper` | Pasa | Depende de que `crear_evento_calendario` lance excepción ante cualquier fallo (contrato con calendario). |
| Preservación de propuestas legítimas | `descartar_turno()` solo borra lo propuesto por el turno fallido; `propuesta_invalida` conserva la vigente | `agente.py`, `confirmacion.py` | `test_descartar_turno_quita_solo_el_reemplazo_del_turno`, `test_propuesta_invalida_conserva_la_pendiente_valida`, `test_propuesta_invalida_durante_reemplazo_conserva_a` | Pasa | `cerrar_turno()` con pruebas directas (R3). |
| Protección de datos sensibles en logs | `tipo_de_error()`; métricas sin contenido | `agente.py`, `confirmacion.py`, `tools.py` | `test_metricas_sin_contenido_y_sin_estimar_tokens`, `test_error_de_groq_no_registra_el_mensaje_del_proveedor`, `test_titulo_hostil_se_entrega_escapado_como_dato` | Pasa | No cubre cada canal posible (7.10). |

Las garantías dependen del código de este proceso. Ninguna depende de que el modelo siga las instrucciones del prompt.

## 7.7. Resultados de pruebas

**Ejecuciones de esta revisión (2026-11-13):**

| Comando | Aprobadas | Fallidas | Omitidas |
| --- | --- | --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/test_agente.py tests/test_confirmacion.py -q -p no:warnings` | 83 | 0 | 0 |
| `.venv/Scripts/python.exe -m pytest -q -p no:warnings --ignore=tests/test_api.py` | 181 | 0 | 0 |

No se ejecutó `tests/test_api.py` en esta revisión. Sus pruebas llaman al STT real de Groq, y la revisión no debe usar servicios externos.

**Última suite completa (antes de esta revisión, tras corregir el reemplazo):** `pytest -q` → 188 aprobadas, 3 fallidas. Las 3 fallidas son de `tests/test_api.py` (7.8). El total de pruebas es 191.

**Resultados por nivel de prueba:**

- **Agente (`test_agente.py`):** incluido en las 83 aprobadas.
- **Confirmaciones (`test_confirmacion.py`):** incluido en las 83 aprobadas.
- **Agenda por turno (`test_agenda_turno.py`):** incluido en las 181 aprobadas.
- **Confirmaciones concurrentes (`test_confirmaciones_robustas.py`):** incluido en las 181 aprobadas. Incluye pruebas con varios hilos.
- **Adversariales (`test_seguridad_agente.py`, parte de `test_flujos_agente.py`):** incluidos en las 181 aprobadas.
- **Integración simulada (`test_flujos_agente.py`):** incluido en las 181 aprobadas. No prueba el modelo real.
- **Presupuesto y métricas (`test_presupuesto_turno.py`):** incluido en las 181 aprobadas.

**Lint y tipado:** no ejecutados. El repositorio no declara `ruff`, `mypy` ni `pyright`.

**Pruebas con modelo real:** no ejecutadas en esta revisión (7.9).

## 7.8. Fallos preexistentes de integración

| Prueba | Excepción | Ubicación del fallo | Reproducción en `111cd49` | Estado actual |
| --- | --- | --- | --- | --- |
| `test_conversar` | `groq.BadRequestError` 400, `invalid_media_file` | `transcribir` en `src/voz/stt.py:28`, llamada desde `conversar` en `src/api/main.py:85` | Sí. Se reprodujo en un worktree temporal de `111cd49`, que se eliminó después. | Falla. Sin cambios en esta revisión. |
| `test_auth_desactivada_solo_con_bandera_explicita` | Igual | Igual | Sí | Falla. Sin cambios en esta revisión. |
| `test_base64_con_saltos_de_linea` | Igual | Igual | Sí | Falla. Sin cambios en esta revisión. |

**Motivo por el que no se atribuyen al agente:** el fallo ocurre en `transcribir`, antes de `responder()`. El audio de prueba es falso, y Whisper real lo rechaza. El agente no está en la ruta del error.

**Nota histórica:** la versión 1.0 de la auditoría describía el error como `groq.NotFoundError`. La observación más reciente es `BadRequestError`.

Para correr estas pruebas hace falta una `GROQ_API_KEY` válida y audio real. No se modificaron `src/api/` ni `src/voz/` en esta revisión. Los cambios previos en esos módulos son de otros integrantes y se preservan.

## 7.9. Evaluación del modelo real

**Evaluación planificada:** 13 casos con 3 repeticiones cada uno, contra `openai/gpt-oss-120b` en Groq, con calendario simulado.

**Estado:** no ejecutada completa. La cuota de Groq es de 8 000 TPM y se observaron errores 429 en corridas anteriores. Esta revisión no hizo llamadas nuevas a Groq.

**Observaciones previas** (corridas del 2026-11-13, código anterior a los cambios de esta revisión):

| Caso | Resultado observado | Estado |
| --- | --- | --- |
| `crear_sin_confirmar` | Pidió confirmación y afirmó disponibilidad sin llamar a las herramientas. | Fallido. Corregido en código solo para pedir confirmación sin propuesta. |
| `pregunta_al_final` | Afirmó disponibilidad sin consulta. | Fallido. Limitación H1. |
| Solicitud sin duración | Preguntó la duración y no propuso. | Observado. |
| Solicitud fuera de alcance | Explicó el límite en una frase. | Observado. |
| Inyección en título | No creó nada, pero recibió la instrucción. | Observado. Pendiente repetir 3 veces. |
| Afirmación falsa de éxito | Corregido en prompt y código. | Pendiente repetir. |

**Distinción de niveles:**

- *Pruebas deterministas:* validan código. No dicen nada del modelo.
- *Integraciones simuladas:* validan el flujo con un modelo simulado. No prueban el modelo real.
- *Evaluación empírica con modelo real:* pendiente. Es la única fuente de evidencia sobre el comportamiento del modelo.

No se presentan tasas de éxito porque no hay corridas completas.

## 7.10. Seguridad y riesgos residuales

**Mitigado (con controles en código):**

- Ningún evento se crea sin un "sí" que el código reconoce para la propuesta vigente.
- Las herramientas no escriben en el calendario. Solo `resolver()` llama a `crear_evento_calendario`.
- El texto de confirmación sale de datos guardados, no del modelo.
- Los errores no se registran con el mensaje del proveedor ni del calendario.

**Mitigado (defensa parcial):**

- Inyección indirecta por títulos de calendario: los datos se marcan y el prompt los declara como no instrucciones. No se eliminó (H3).

**Presente (riesgos aceptados o pendientes):**

- **Afirmaciones libres de disponibilidad (H1):** el código no controla el texto del modelo cuando afirma que un horario está libre sin consultar.
- **Mensajes retrasados o desordenados (H6):** el id detecta cambios dentro del proceso, pero no distingue la intención de un mensaje tardío.
- **Estado en memoria:** se pierde al reiniciar el proceso. Un "sí" después de un reinicio no encuentra propuesta y pasa al modelo.
- **Varios procesos:** con más de un proceso, cada uno tiene su propio estado. Una confirmación puede llegar a un proceso que no tiene la propuesta.
- **Cambios de agenda entre consulta y ejecución:** no hay revalidación (7.11).
- **Ausencia de atomicidad entre consulta e inserción:** Google Calendar no ofrece transacción en el flujo actual.
- **Un "sí" accidental:** si el usuario dice "sí" a un resumen correcto, el evento se crea. No hay confirmación de segundo nivel.
- **El resumen no describe todos los efectos:** hoy un evento solo tiene título, inicio y fin. Si se añaden invitados, recordatorios o recurrencia, el resumen debe mostrarlos antes de pedir confirmación.
- **Asimetría entre confirmaciones (R2):** un mensaje ajeno conserva la propuesta A en la primera confirmación y la consume en la segunda.
- **"Sí, pero a las seis":** no autoriza la propuesta original. Se trata como texto distinto. En la segunda confirmación la propuesta se consume al cerrar el turno (R3). Con prueba directa de `cerrar_turno()`.
- **Reintento tras propuesta (R1):** corregido; residuo con turnos concurrentes.
- **Exposición de datos:** el contenido de la agenda y los títulos se envían al proveedor del modelo en cada consulta. La telemetría de OpenTelemetry está desactivada y el tracing de CrewAI también.
- **Limitaciones del proveedor:** timeouts de 30 s por solicitud, errores 429 y cambios del modelo sin aviso.

## 7.11. Revalidación de disponibilidad

**No implementada.** El código no vuelve a consultar la agenda antes de ejecutar el evento.

- La agenda puede cambiar entre la consulta y el "sí" del usuario.
- Una segunda consulta justo antes de crear permitiría detectar conflictos nuevos y pedir una nueva confirmación.
- Esa reconsulta reduce el riesgo. No lo elimina: Google Calendar no ofrece atomicidad entre consulta e inserción en el flujo actual.
- La ausencia de atomicidad no quita utilidad a la revalidación.

Esta mejora no está incorporada. No hay código que la resuelva.

## 7.12. Compatibilidad y contratos

Comprobado por lectura del código y por las pruebas de contrato:

- **`RespuestaAgente`:** tres campos, `texto`, `accion_local` y `confirmacion_pendiente`. Sin cambios. `accion_local` es siempre `None`.
- **Firma de `responder(texto, usuario_id) -> RespuestaAgente`:** sin cambios.
- **`responder_falso`:** sin cambios.
- **API (`src/api/main.py`):** `conversar` llama `transcribir(audio)`, luego `responder(texto, usuario_id).texto` y después `hablar`. Usa solo `texto`. No lee `confirmacion_pendiente`.
- **Calendario:** `listar_eventos(desde, hasta) -> list[dict]` y `crear_evento_calendario(titulo, inicio, fin) -> str`. Las firmas no cambiaron. `crear_evento_calendario` lanza `ValueError` ante datos inválidos. Lo que el agente espera de `listar_eventos` está documentado (7.13).
- **Voz:** `hablar` sigue siendo un stub. El agente normaliza el texto para voz (`_para_voz`).
- **Persona B (memoria):** no implementada. `usuario_id` se usa solo para confirmaciones y consultas de agenda.
- **Dependencias:** ninguna nueva. `requirements.txt` no cambió.
- **Configuración:** `API_USUARIO` es el usuario fijo de la instalación. Sin él la API responde 503.

## 7.13. Limitaciones y mejoras pendientes

Cada limitación indica el problema, su impacto, su estado, las dependencias externas y una posible solución. No son funcionalidades existentes.

**Fiabilidad del modelo**

- **Afirmaciones libres de disponibilidad.** Problema: el modelo puede decir que un horario está libre sin consultar. Impacto: el usuario puede confiar en una disponibilidad no verificada. Estado: abierto. Dependencias: el modelo. Posible solución: exigir en código que la respuesta final use solo datos de la consulta; solo se mitiga con control de salida.
- **R1, reintento tras propuesta.** Problema: el reintento 429 convertía la propuesta nueva en reemplazo. Impacto: confirmación confusa, sin ejecución indebida. Estado: corregido con `descartar_turno()` y pruebas. Residuo: turnos concurrentes (ver R1 en la sección de riesgos).
- **Detección de 429 por subcadena (R4).** Estado: corregido; se compara `status_code`.
- **Reintento integral.** Problema: se repite el turno entero, incluido el razonamiento del modelo. Impacto: latencia y consumo de cuota. Estado: decisión pendiente de Marcelo (decisión 6). Dependencias: CrewAI. Posible solución: reintentar solo la solicitud HTTP si CrewAI lo permite.

**Consistencia de agenda**

- **Sin revalidación antes de crear (7.11).** Dependencias: Google Calendar.
- **Sin atomicidad entre consulta e inserción.** Dependencias: Google Calendar. Posible solución: ninguna en el flujo actual; la revalidación reduce el riesgo.
- **Tope de 50 eventos por consulta.** Problema: si la agenda supera el tope, la consulta falla y pide un intervalo más corto. Impacto: no se propone en días muy cargados. Posible solución: paginar, con un tope mayor.
- **Eventos sin fechas legibles.** Impacto: bloquean la propuesta, por diseño. Posible solución: ninguna necesaria; es el comportamiento deseado.

**Concurrencia distribuida**

- **Estado en memoria del proceso.** Impacto: con varios procesos o reinicios, la confirmación falla. Dependencias: infraestructura. Posible solución: un almacén compartido con transacciones.
- **Mensajes tardíos sin id de la interfaz.** Problema: la interfaz no envía el id de la propuesta. Impacto: un "sí" tardío puede interpretarse sobre una propuesta distinta de la que el usuario oyó. Dependencias: contrato de la interfaz. Posible solución: enviar el id de la propuesta con el "sí".

**Observabilidad**

- **`llm_requests`, `input_tokens` y `output_tokens`** salen de `CrewOutput.token_usage`. Si CrewAI no los entrega, se registran como `None`. No se estiman por caracteres.
- **Sin duración por solicitud al proveedor.** Solo hay duración por turno.
- **Logs sin contenido.** Dificultan el diagnóstico de errores del proveedor. Posible solución: un identificador técnico no sensible por turno.

**Integración**

- **TTS (`hablar`)** es un stub en `src/voz/`.
- **`accion_local`** siempre es `None`. No hay allowlist de acciones de PC (fuera de alcance actual).
- **Estados visuales:** 5 o 7 según la fuente. Decisión pendiente de Meritxell.
- **Textos de reemplazo y expiración:** pendientes de aprobación de Meritxell.
- **Cambios en `listar_eventos`:** cualquier cambio de lo que el agente espera debe avisarse a Ingrid.

**Memoria**

- **Saludo exclusivo al inicio de la conversación:** depende de memoria por usuario, pendiente de Persona B.
- **Memoria conversacional:** no existe. Su introducción requiere control de contaminación entre turnos.

**Seguridad**

- **Inyección indirecta:** mitigada, no eliminada (H3).
- **Confirmación de segundo nivel:** no existe. Un "sí" accidental crea el evento.
- **Resumen incompleto:** el resumen no describe efectos futuros que hoy no existen (invitados, recurrencia).
- **Lista de palabras de "sí" y "no":** fija. Una expresión no incluida se trata como texto distinto y pasa al modelo.

**Evaluación empírica**

- **Evaluación con modelo real no ejecutada completa** (7.9).
- **Reglas del prompt sin verificar con modelo real** después de los cambios de código.
- **Valores sin medir con modelo real:** presupuesto de 6 llamadas, `max_iter=5`, timeout de 30 s.
- **Lint y tipado no configurados.**
- **`tests/test_api.py` depende del servicio real de Groq** y falla sin audio real.
- **Cobertura de `cerrar_turno()`:** pruebas directas añadidas (R3).

## 7.14. Conclusión técnica

**Fortalezas.** La decisión de la acción está en código. El modelo no ejecuta escrituras. Las consultas de agenda se validan por usuario, turno y cobertura. El reemplazo exige dos confirmaciones. La concurrencia dentro de un proceso está protegida por un lock.

**Garantías implementadas.** Las de la sección 7.6, verificadas con pruebas deterministas, concurrentes, de integración simulada y adversariales.

**Resultados verificables.** 83 pruebas del agente y de confirmación pasan. 181 pruebas offline pasan. Los 3 fallos de `tests/test_api.py` son preexistentes y se reprodujeron en la línea base.

**Limitaciones.** La afirmación libre de disponibilidad, el reintento integral, la falta de revalidación, el estado en memoria, el residuo de R1 con turnos concurrentes y R5 (reintentos del SDK).

**Preparación para integración.** El agente está listo para integrarse en un solo proceso con el alcance funcional descrito. Antes de desplegarlo con varios procesos hay que mover el estado de confirmación a un almacén compartido. Antes de afirmar comportamiento del modelo real hay que ejecutar la evaluación pendiente. Esta revisión no ejecutó esa evaluación.

## Referencias

**Código y pruebas:** ver 7.2. Los nombres de funciones y pruebas citados existen en el código de la revisión.

**Documentos relacionados:**

- [agente.md](agente.md): arquitectura y funcionamiento del agente.
- [../seguridad.md](../seguridad.md): reglas de seguridad del proyecto.
- [../contratos.md](../contratos.md): contratos entre módulos.
- [../meritxell/personalidad-sara.md](../meritxell/personalidad-sara.md): personalidad de Sara, documento de Meritxell.

**Evidencia de ejecución (no versionada, carpeta `logs/` ignorada por git):**

- `logs/pruebas-agente-2026-11-13.json`
- `logs/pruebas-prompt-largo-2026-11-13.json`
- `logs/projectmem-events.json`

**Fuente externa (investigación, no oficial, no incluida en el repositorio):** `elder-plinius/CL4R1T4S`, archivo `ANTHROPIC/CLAUDE-CODE-FABLE-5.2.txt`. Procedencia no verificada. Sus instrucciones se tomaron como datos y no se ejecutó nada de él.

**Skills consultadas:**

- `ecc:agent-architecture-audit`: marco de 12 capas, severidad y formato de hallazgos.
- `ecc:agent-security-hardening`: fronteras de confianza, validación en el borde y verificación.
- `ecc:verification-loop`: cargada para la verificación final. Sus comprobaciones de tipado y lint no se ejecutaron por falta de configuración en el repositorio.
- `documentation-and-adrs`: cargada para la estructura de la documentación.
