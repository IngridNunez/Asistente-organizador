# Etapa 1: voz en el PC

Objetivo: grabar voz en el PC, transcribirla, que el agente responda algo
simple (sin herramientas todavía) y escuchar la respuesta en voz.

## Grupo Voz
- [ ] Definir STT final (Whisper/Groq, faster-whisper local o Web Speech API)
      y dejarlo documentado en `.env.example` / `requirements.txt`.
- [ ] Implementar `transcribir(audio) -> str` en `src/voz/stt.py`.
- [ ] Elegir motor de TTS (edge-tts o Piper).
- [ ] Implementar `hablar(texto) -> bytes` en `src/voz/tts.py`.
- [ ] Probar el ciclo completo: grabar -> transcribir -> hablar -> escuchar.

## Grupo Agente
- [ ] Armar el prompt base del asistente (tono, qué puede y no puede hacer).
- [ ] Implementar `responder(texto, usuario_id) -> str` en
      `src/agente/agente.py` con LangChain (sin herramientas todavía).
- [ ] Agregar memoria de conversación simple (por `usuario_id`).
- [ ] Probar que mantiene contexto entre 2-3 mensajes seguidos.

## Grupo Herramientas
- [ ] Mientras no hay nada que llamar en etapa 1, revisar la Google
      Calendar API (scopes, OAuth) para preparar la etapa 2.
- [ ] Documentar en `docs/seguridad.md` cualquier riesgo que identifiquen
      para el acceso al PC (etapa 4), aunque todavía no se implemente.

## Interfaz
- [ ] Decidir interfaz definitiva (web/Gradio-Streamlit, Telegram o ambas)
      y actualizar `src/interfaz/`.
- [ ] Construir el botón de "grabar" y la reproducción de la respuesta,
      consumiendo `POST /conversar` de la API.

## Integración (coordinadora)
- [ ] Levantar la API (`src/api/main.py`) con `uvicorn` y probar
      `POST /conversar` end to end con los stubs.
- [ ] Reemplazar los stubs por las implementaciones reales a medida que
      cada grupo termine, sin cambiar las firmas de `docs/contratos.md`.
- [ ] Armar el tablero en GitHub Projects con estas tareas como issues.
