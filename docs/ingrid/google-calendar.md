# Google Calendar: credenciales y autorización

**Versión 1.0** · 2026-11-08 · Autora: Ingrid (Herramientas A, calendario)

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-11-08 | Primera versión: credenciales, autorización, permiso, consola y problemas frecuentes. |

Guía para que cada integrante pueda usar el calendario real (`src/herramientas/calendario.py`).
Aquí no hay ningún valor real: el ID, el secreto y el token nunca se escriben en el repo.

## Qué credenciales existen y dónde viven

| Qué es | Para qué sirve | Dónde vive | ¿Se sube a git? |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | Identifica a la app S.A.R.A ante Google | Tu `.env` local | No |
| `GOOGLE_CLIENT_SECRET` | Secreto de la app | Tu `.env` local | No |
| Token (`token.json`) | Permiso de **tu cuenta** para que la app use **tu** calendario | `~/.sara/token.json` (en Windows: `C:\Users\<usuario>\.sara\token.json`) | No |
| `GOOGLE_TOKEN_PATH` | Opcional: otra carpeta para guardar el token | Tu `.env` local | No |

El ID y el secreto son los mismos para todo el equipo (son de la app). El token es **personal**: cada uno
autoriza con su propia cuenta `@duocuc.cl` y el token queda solo en su computador.

El `.env` está en `.gitignore`, y `credentials.json`, `client_secret*.json` y `token.json` también.
Los nombres de las variables (sin valores) están en `.env.example`.

## Cómo conseguir el ID y el secreto

El ID y el secreto los entrega **quien administra el proyecto de Google Cloud** (hoy, Ingrid) por un canal
privado. **Nunca** por el chat del grupo, por correo sin cuidado ni dentro del repo.

Si eres tú quien lo administra, o necesitas crearlo de nuevo, estos son los pasos:

1. Entra a [console.cloud.google.com](https://console.cloud.google.com) con una cuenta `@duocuc.cl`.
2. **Proyecto nuevo**: nombre `SARA` (el nombre no admite puntos), organización `duocuc.cl`.
3. **APIs y servicios → Biblioteca**: busca **Google Calendar API** y presiona **Habilitar**.
4. **Pantalla de consentimiento de OAuth**:
   - Nombre de la aplicación: `S.A.R.A`.
   - Correo de asistencia y de contacto: el del administrador.
   - Público: **Interno**. Así cualquier cuenta `@duocuc.cl` puede autorizar, sin lista de usuarios de
     prueba, y el token no caduca a los 7 días como en las apps externas en modo de prueba.
5. **Credenciales → Crear credenciales → ID de cliente de OAuth**: tipo **Aplicación de escritorio**.
6. Descarga el JSON y guárdalo **fuera del repo y fuera de OneDrive** (por ejemplo en `~/.sara/`).
   De ahí salen `client_id` y `client_secret`, que van al `.env` de cada persona.

No actives la prueba gratuita ni la facturación de Google Cloud: la Calendar API es gratuita y no lo necesita.

## Configuración de cada integrante

1. Python 3.12 y el entorno virtual activo (ver `README.md`):
   ```powershell
   uv venv --python 3.12 .venv
   .venv\Scripts\activate
   uv pip install -r requirements.txt
   ```
   Con `uv venv` el entorno no trae `pip`: instala con `uv pip install`, no con `pip install`.
2. Copia `.env.example` como `.env` y completa:
   ```text
   GOOGLE_CLIENT_ID=<te lo pasa el administrador>
   GOOGLE_CLIENT_SECRET=<te lo pasa el administrador>
   ```
   `GOOGLE_TOKEN_PATH` déjalo vacío salvo que quieras guardar el token en otra carpeta.
3. Autoriza **una sola vez**, con el entorno activo y desde la raíz del repo:
   ```powershell
   python -m src.herramientas.calendario
   ```
   Se abre el navegador: elige tu cuenta `@duocuc.cl` y acepta. La terminal debe decir
   `Autorizado. Token guardado en ...`.
4. Listo. El token se renueva solo; no hay que volver a autorizar.

Solo hay que repetir la autorización si borras `token.json`, cambias la contraseña de tu cuenta de Google
o revocas el acceso desde tu cuenta.

## Qué hay que pasarle a cada integrante

El administrador entrega, **por un canal privado** (mensaje directo, nunca el grupo ni el repo), solo estos dos valores:

- [ ] `GOOGLE_CLIENT_ID`
- [ ] `GOOGLE_CLIENT_SECRET`

Todo lo demás es personal y lo consigue cada uno:

| Cosa | Quién la consigue |
|---|---|
| `GROQ_API_KEY` | Cada uno, con su propia cuenta gratuita de Groq |
| `token.json` | Cada uno, al autorizar con su cuenta `@duocuc.cl` (paso 3 de arriba) |
| `API_AUTH_TOKEN` | Cada uno, generado en local (ver `.env.example`) |

## Probar el agente por consola (solo texto)

Sirve para conversar con el agente sin voz ni interfaz. Necesita `GROQ_API_KEY` en el `.env` y estar en una
rama que tenga `src/agente/` (la del agente o `develop` cuando esté unida).

1. Guarda este código como `conversar.py` **fuera del repo** (por ejemplo en `~/.sara/conversar.py`):

   ```python
   import sys
   from pathlib import Path

   # El script vive fuera del repo: se agrega la carpeta actual para poder importar `src`.
   sys.path.insert(0, str(Path.cwd()))

   from src.agente.agente import responder  # noqa: E402

   print("Habla con el agente. Escribe 'salir' para terminar.\n")
   while True:
       texto = input("tú> ").strip()
       if texto.lower() in ("salir", "exit", "q"):
           break
       respuesta = responder(texto, "consola")
       print(f"sara> {respuesta.texto}")
       if respuesta.confirmacion_pendiente:
           print("      (esperando tu sí o no)")
       print()
   ```

2. Con el entorno activo y **desde la raíz del repo**:

   ```powershell
   python $env:USERPROFILE\.sara\conversar.py
   ```

3. Ejemplos para probar: *"¿qué tengo esta semana?"*, *"agéndame una prueba mañana a las 5"* y luego *"sí"* o *"no"*.

Ojo: los eventos que confirmes con "sí" se crean **de verdad** en tu Google Calendar. Bórralos después.
Cada respuesta usa un poco de tu cuota gratuita de Groq.

## Qué permiso se pide

`https://www.googleapis.com/auth/calendar.events`: leer y crear eventos. Es el mínimo necesario. No se pide
`calendar` completo (que permitiría borrar o modificar calendarios enteros).

## Cómo funciona con el agente

- El agente solo **propone** crear un evento. El evento se crea cuando el usuario responde "sí" y lo ejecuta
  el código (`confirmacion.py`), nunca el modelo directamente.
- Las fechas sin zona horaria se interpretan como `America/Santiago`.
- Sin credenciales, `calendario.py` falla con un mensaje claro. Para trabajar sin Google, en
  `src/agente/confirmacion.py` se puede volver al stub: `from src.herramientas import calendario_falso as calendario`.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Faltan GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET` | El `.env` no tiene los valores, o no estás en la raíz del repo. |
| `No matching distribution found for crewai` | Estás usando Python 3.14 o el pip global. Usa Python 3.12 en `.venv` e instala con `uv pip install -r requirements.txt`. |
| Google muestra "acceso bloqueado" | La cuenta no es de la organización `duocuc.cl`, o el administrador de Duoc restringe apps de terceros. |
| El navegador no se abre | Corre la autorización desde una máquina con navegador, no desde un servidor sin pantalla. |
| Dejó de funcionar tras semanas | Borra `~/.sara/token.json` y vuelve a autorizar. |

## Seguridad

- Nunca pegues el secreto ni el contenido de `token.json` en chats, issues, PR ni capturas.
- Si el secreto se filtra, el administrador debe **rotarlo**: en Google Cloud, *Credenciales →* el ID de cliente →
  agregar un secreto nuevo y desactivar el anterior. Después todos actualizan su `.env`.
- Trata `token.json` como una contraseña: da acceso a tu calendario.
- El token y las credenciales viven fuera del repo y no se guardan en carpetas sincronizadas (por ejemplo OneDrive).
