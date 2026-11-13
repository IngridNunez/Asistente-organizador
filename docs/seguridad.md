# Seguridad

Reglas obligatorias para todo el equipo:

- Nada de "acceso completo al PC". Cada acción sobre el PC es una función
  específica, con lista de acciones permitidas (allowlist), nunca comandos
  libres generados por el modelo.
- Prohibido usar `eval`, `exec`, `os.system` o `subprocess` con texto que
  venga directa o indirectamente del LLM.
- Acciones delicadas (borrar, enviar, modificar algo fuera de la lectura)
  requieren confirmación explícita del usuario antes de ejecutarse.
- Cuidado con prompt injection: el contenido que llega por voz/texto del
  usuario (o de una herramienta, ej. el cuerpo de un evento de calendario)
  nunca debe tratarse como instrucción del sistema.
- Si la API queda expuesta a internet, debe exigir autenticación
  (`API_AUTH_TOKEN` en `.env`; el usuario es fijo por `API_USUARIO`, ver `src/api/main.py`).
- Ninguna clave o token se sube a git: todo vive en `.env` (ignorado) y se
  documenta sin valores reales en `.env.example`.
- La voz del usuario viaja a un servicio externo (STT/LLM/TTS en la nube):
  evitar mandar información sensible innecesaria y avisar a los usuarios de
  prueba qué servicios reciben su audio.
