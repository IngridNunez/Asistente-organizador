# Avances de Felix (Módulo de Memoria de Conversaciones)

**Versión 1.0** · 2026-11-09

## 2026-11-09

- **Qué hice (paso a paso):**
  - **Paso 1: Revisé la arquitectura actual del repositorio** (`AGENTS.md`, `docs/contratos.md`, `README.md`) para entender cómo se integran los módulos auxiliares y las directrices de diseño (etapas 1-4, uso de memoria RAM por proceso).
  - **Paso 2: Definí el diseño de `memoria.py`** decidiendo almacenar una estructura acotada de turnos (`TurnoConversacion`) con límite estricto por ventana deslizante.
  - **Paso 3: Escribí `src/agente/memoria.py`**: 
     - Creé la `dataclass` para representar cada turno (mensaje de usuario, respuesta del asistente y timestamp UTC).
     - Configuré un diccionario interno en memoria `_HISTORIAL` mapeado por `usuario_id`.
     - Implementé el límite estricto de `MAX_CONVERSACIONES = 3` usando comportamiento FIFO para descartar los turnos más antiguos automáticamente.
     - Añadí funciones públicas tipadas: `guardar_turno`, `obtener_historial`, `obtener_historial_formateado`, `cantidad_conversaciones` y `limpiar_memoria`.
  - **Paso 4: Escribí `tests/test_memoria.py`** para validar de forma aislada y rigurosa la lógica:
     - Comprobación del almacenamiento secuencial de 1 a 4 turnos.
     - Verificación de que la ventana se mantiene exactamente en los últimos 3 turnos.
     - Comprobación del aislamiento estricto de la memoria entre distintos `usuario_id`.
     - Pruebas del formateo de texto y de la función de limpieza.

- **Decisiones y por qué:**
  - **Cero impacto colateral:** Se respetó estrictamente la instrucción de no modificar ningún archivo existente en el proyecto (`src/agente/agente.py`, `src/api/main.py`, etc.). Todo el desarrollo se aisló en el nuevo módulo y su test.
  - **Ubicación en singular:** Se colocó en `src/agente/memoria.py` de acuerdo con la arquitectura actual del repositorio (singular `agente`, no plural).
  - **Memoria en RAM por proceso:** Sigue el estándar de otros módulos auxiliares existentes (como `confirmacion.py`), ideal para las etapas iniciales del desarrollo del asistente.
  - **Ventana de 3 turnos:** Permite recordar el contexto inmediato de la charla por voz sin sobrecargar el contexto del modelo LLM ni consumir recursos ilimitados.

- **Qué falta o qué me bloquea:**
  - Integrar el uso de `obtener_historial_formateado(usuario_id)` dentro del prompt del agente (cuando se decida conectar con la lógica del modelo).
  - Validar el comportamiento con el equipo en la siguiente revisión conjunta.

## Verificación del Módulo

Ejecución de pruebas unitarias específicas para comprobar el funcionamiento del nuevo módulo:

```powershell
pytest tests/test_memoria.py -v
```

Resultado esperado: Todos los tests pasan correctamente de forma aislada, garantizando la robustez del almacenamiento temporal y el control de la ventana deslizante.

## Observaciones e Ideas para más adelante

1. **Persistencia opcional:** Si en el futuro el asistente requiere recordar sesiones entre reinicios del servidor, se podría extender `memoria.py` para respaldar el historial en una base de datos ligera (como SQLite), manteniendo la misma interfaz pública para no romper contratos.
2. **Control de expiración por tiempo:** Añadir opcionalmente un tiempo de expiración (TTL) por inactividad del usuario, para limpiar automáticamente memorias de conversaciones abandonadas.