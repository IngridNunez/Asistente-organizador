# Interfaz web de S.A.R.A.

La aplicación React + Vite vive en `src/interfaz/web/`, separada del paquete
Python `src/interfaz`. Usa Tailwind CSS 3 y las siete ilustraciones locales de
`src/interfaz/web/src/assets/sara/`.

## Desarrollo local

1. Configura el `.env` de la raíz según `.env.example`. La API necesita
   `API_USUARIO`; para autenticación, configura `API_AUTH_TOKEN` o desactívala
   solo para desarrollo local con `API_AUTH_DISABLED=true`.
2. En una terminal, activa el entorno Python y ejecuta:

   ```powershell
   uvicorn src.api.main:app --reload
   ```

3. En otra terminal, instala y levanta la interfaz:

   ```powershell
   cd src\interfaz\web
   npm install
   npm run dev
   ```

El proxy de Vite reenvía `/api/conversar` a `http://127.0.0.1:8000/conversar`.
Puede apuntarse a otro servidor con `API_URL` en el `.env` de la raíz. Si
`API_AUTH_TOKEN` está definido allí, Vite lo agrega en el servidor; la variable
no se incluye en el JavaScript enviado al navegador. No crear una variable
`VITE_API_AUTH_TOKEN` ni exponer el token en el cliente.

El navegador solicita permiso para usar el micrófono. La grabación se convierte
a WAV mono de 16 kHz antes de enviarse, que es el formato que espera la
transcripción actual. El navegador debe acceder a la aplicación mediante
`localhost` o HTTPS.

El proxy configurado en Vite es solo para desarrollo. Al publicar `dist/`, el
servidor que aloje la interfaz debe reenviar `/api/conversar` a FastAPI y añadir
la autenticación desde el servidor; nunca se debe compilar el token en el
frontend.

## Límites del contrato actual

`POST /conversar` solo devuelve texto y audio; todavía no comunica si hay una
confirmación pendiente ni qué acción se ejecutó. La interfaz no presenta
botones de confirmación ni afirma que una acción haya tenido éxito. Cuando la
respuesta acaba en signo de interrogación, permite responder hablando. El TTS
actual también es un stub y entrega audio vacío, así que por ahora la respuesta
se presenta en pantalla.

Para compilar la aplicación:

```powershell
npm run build
```
