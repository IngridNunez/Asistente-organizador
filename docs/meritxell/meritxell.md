# Avances de Meritxell (Interfaz web de S.A.R.A.)

**Versión 1.0** · 2026-11-19

## Estado de las tareas ([`docs/etapa1.md`](../etapa1.md), Interfaz)

- [x] Implementar una interfaz web con React, Vite y Tailwind CSS 3 en [`src/interfaz/web/`](../../src/interfaz/web/).
- [x] Separar la pantalla en componentes y usar las siete ilustraciones locales de S.A.R.A.
- [x] Grabar audio desde el navegador y enviarlo a `POST /conversar`.
- [x] Agregar un proxy de desarrollo para conectar Vite con FastAPI sin exponer el token al navegador.
- [ ] Probar una conversación real desde el navegador con micrófono, Groq y autenticación configurados.
- [ ] Integrar el TTS real cuando esté disponible.
- [ ] Acordar con el equipo cómo representar las confirmaciones que devuelve el agente.
- [ ] Configurar el proxy autenticado del servidor de producción; el proxy de Vite solo se usa en desarrollo.

## 2026-11-19

- **Qué hice (paso a paso):**
  - **Paso 1: Revisé el prototipo de Stitch.** Usé `code.html` como referencia de diseño y adapté la interfaz al repositorio existente, sin copiar el prototipo HTML con React y Babel cargados desde CDN.
  - **Paso 2: Creé la aplicación en [`src/interfaz/web/`](../../src/interfaz/web/).** Configuré React, Vite, Tailwind CSS 3, Font Awesome y las fuentes del diseño. El cliente web queda separado del backend Python.
  - **Paso 3: Organicé los componentes.** Separé el avatar, el botón de micrófono, el mensaje de respuesta y el botón para reintentar después de un error.
  - **Paso 4: Integré las ilustraciones.** Copié los siete estados de S.A.R.A. a [`src/interfaz/web/src/assets/sara/`](../../src/interfaz/web/src/assets/sara/) y los importé como assets locales, en vez de depender de URLs de imágenes externas.
  - **Paso 5: Implementé la captura de voz.** El navegador solicita permiso para usar el micrófono. La grabación se convierte a WAV mono de 16 kHz, se codifica en Base64 y se envía en el formato que espera `POST /conversar`.
  - **Paso 6: Conecté el cliente con FastAPI en desarrollo.** El proxy de Vite reenvía `/api/conversar` al endpoint `/conversar` y agrega `API_AUTH_TOKEN` en el servidor, no en el código del navegador. Se puede cambiar el destino con `API_URL`.
  - **Paso 7: Añadí estados de interfaz y errores.** La pantalla refleja grabación, procesamiento, respuesta, cancelación y error; también muestra el texto devuelto y reproduce audio si la API lo entrega.
  - **Paso 8: Evité afirmaciones de éxito sin respaldo.** Quité del prototipo los paneles de desarrollo, las URLs externas y los textos que afirmaban que el calendario estaba conectado o que una acción ya se había completado.
  - **Paso 9: Documenté instalación, ejecución y límites** en [`docs/interfaz-web.md`](interfaz-web.md) y actualicé las instrucciones del proyecto en [`README.md`](../../README.md).

- **Decisiones y por qué:**
  - La interfaz es una aplicación web React + Vite; no crea un segundo proyecto en la raíz ni reemplaza la API FastAPI.
  - El navegador envía WAV mono de 16 kHz porque [`src/voz/stt.py`](../../src/voz/stt.py) entrega el audio a Groq con MIME `audio/wav`.
  - El token no usa una variable `VITE_*`: esas variables se incorporan al frontend y podrían quedar visibles para quien visite la página.
  - La API actual devuelve texto y audio, pero no informa una confirmación pendiente de forma estructurada. Por eso la interfaz no declara que una acción se haya ejecutado ni muestra controles de confirmación de calendario.
  - El TTS conectado en la API sigue siendo `hablar_falso`; mientras devuelva audio vacío, la interfaz solo presenta la respuesta escrita.

## Verificación

- `npm install` y `npm run build` en `src/interfaz/web/`: compilación de producción exitosa.
- `.venv\Scripts\python.exe -m pip install -r requirements.txt`: dependencias instaladas con Python 3.12.14.
- `.venv\Scripts\python.exe -m pytest`: **238 pruebas aprobadas**.
- Inicié FastAPI y Vite localmente. La página de Vite, `openapi.json` de FastAPI y el endpoint del proxy de desarrollo respondieron HTTP 200.
- La prueba de una conversación hablada real queda pendiente; no se envió audio a Groq durante estas verificaciones.

## Qué falta o qué me bloquea

- **Prueba integral de voz.** Probar desde el navegador con permisos de micrófono, `GROQ_API_KEY`, `API_USUARIO` y autenticación local correctamente configurados.
- **TTS.** La interfaz ya puede reproducir el audio no vacío de la respuesta, pero el backend usa un stub que no genera voz.
- **Confirmaciones.** Coordinar con el equipo del agente/API un campo explícito para `confirmacion_pendiente` antes de implementar el flujo de sí/no para crear eventos.
- **Publicación.** En producción, configurar en el servidor un proxy hacia FastAPI que añada la autenticación. La configuración actual de proxy es exclusiva de Vite en desarrollo; nunca se debe publicar el token en el frontend.
- **Revisión visual y de navegadores.** Comparar la pantalla con `screen.png` de Stitch y verificar micrófono y diseño en los navegadores que se usarán para la entrega.
- **Integración con el equipo.** Subir los cambios en una rama de feature y abrir un PR hacia `develop`, como indica el flujo del repositorio.

## Cómo probar localmente

1. Configurar el `.env` de la raíz según [`docs/interfaz-web.md`](interfaz-web.md).
2. En una terminal, activar el entorno Python y ejecutar `uvicorn src.api.main:app --reload`.
3. En otra terminal:

   ```powershell
   cd src\interfaz\web
   npm install
   npm run dev
   ```

4. Abrir la dirección local que muestra Vite y permitir el acceso al micrófono.
