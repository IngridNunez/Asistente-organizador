# Agente de voz

Asistente personal de voz (tipo Siri/Alexa) para el proyecto final del
track de IA. Flujo: botón de escucha -> grabar voz -> transcribir (STT)
-> agente (LLM + herramientas) -> texto a voz (TTS).

## Arquitectura

Un agente corre como API (FastAPI) en un servidor, y cada dispositivo
(PC, celular) tiene un cliente liviano que graba audio, lo manda a la
API y reproduce la respuesta. El cliente local es el único que puede
ejecutar acciones sobre ese dispositivo (ver `docs/seguridad.md`).

```
cliente (PC/celular) --audio--> API (FastAPI) --LLM + herramientas--> respuesta
        ^                                                                |
        |-------------------------- audio de respuesta -------------------|
```

## Estructura del repo

```
agente-voz/
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── src/
│   ├── voz/            # STT y TTS
│   ├── agente/          # prompt, memoria, LangChain
│   ├── herramientas/    # Google Calendar, acceso al PC
│   ├── api/             # FastAPI, endpoint /conversar
│   └── interfaz/        # botón y pantalla (web/Telegram)
├── tests/
└── docs/
    ├── contratos.md     # firmas de funciones entre módulos
    ├── seguridad.md      # reglas obligatorias de seguridad
    └── etapa1.md         # tareas de la primera etapa
```

## Cómo empezar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # completar con las claves reales
```

Levantar la API:
```bash
uvicorn src.api.main:app --reload
```

Correr los tests:
```bash
pytest
```

## Equipo y roles

- **Voz** (2): transcripción (STT) y texto a voz (TTS).
- **Agente** (2): prompt, memoria y planificación con LangChain.
- **Herramientas** (2): Google Calendar y acceso controlado al PC.
- **Interfaz** (1): botón y pantalla de la app.
- **Coordinación e integración** (Ingrid): revisión de PRs e integración entre módulos.

## Etapas del proyecto

1. Voz en el PC (grabar, transcribir, responder, hablar) — ver `docs/etapa1.md`.
2. Calendario.
3. Memoria y planificación ("organiza mi semana").
4. Acceso controlado al PC.
5. Celular.

## Flujo de trabajo

Se utiliza una técnica de branches para el trabajo colaborativo:

- `main`: siempre estable, lista para entregar/demostrar.
- `develop`: rama de integración, donde se juntan los avances de todos antes
  de pasar a `main`.
- `feature/nombre`: cada persona trabaja su tarea en su propia rama, creada
  desde `develop`.
- Pull Request de `feature/nombre` -> `develop` revisado antes de unir.
  `develop` -> `main` se hace cuando hay una versión estable para mostrar.
- Tablero en GitHub Projects (Por hacer / En progreso / En revisión / Listo).
- Reunión corta semanal.

## Seguridad

Ver `docs/seguridad.md`. En resumen: nada de acceso libre al PC, nada de
`eval` ni comandos generados por el modelo, confirmación antes de acciones
delicadas, cuidado con prompt injection, y ninguna clave en el repo
(`.env` está en `.gitignore`).

## Contratos entre módulos

Ver `docs/contratos.md` para las firmas exactas (`transcribir`, `responder`,
`hablar`, herramientas y el endpoint `/conversar`), más los stubs ("falsos")
que cada equipo puede usar mientras el módulo real no está listo.

## Pendiente por decidir

- Interfaz definitiva (web o Telegram).
- Funciones de celular que se necesitan (define si hace falta una app Android).
- Entrega estimada: dentro de 7 semanas aprox. (ajustar cronograma de `docs/etapa1.md` en adelante).
