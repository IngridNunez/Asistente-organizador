import os
from datetime import datetime
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Versión real de las herramientas de calendario (mismas firmas que calendario_falso.py,
# ver docs/contratos.md). Cuando esté probada, confirmacion.py solo cambia su import.

load_dotenv()

# Permiso mínimo: leer y crear eventos. No pedimos "calendar" completo (borrar calendarios, etc.).
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Las fechas sin zona horaria que manda el LLM se interpretan en esta zona.
ZONA_HORARIA = "America/Santiago"

# El token es personal de cada usuario y vive fuera del repo (nunca se sube a git).
RUTA_TOKEN = Path(os.getenv("GOOGLE_TOKEN_PATH") or Path.home() / ".sara" / "token.json")

MAX_EVENTOS = 50  # tope de eventos que se le devuelven al agente por consulta
MAX_CHARS_TITULO = 200  # el título viene del LLM: se acota para no escribir basura en el calendario


# Devuelve credenciales válidas. La primera vez abre el navegador para que el usuario autorice;
# después reutiliza (y renueva si hace falta) el token guardado.
def _credenciales() -> Credentials:
    creds = None
    if RUTA_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(RUTA_TOKEN), SCOPES)
    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError(
                "Faltan GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET en el entorno (.env)"
            )
        config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(config, SCOPES)
        # Con una app de escritorio siempre devuelve Credentials; cast() solo acota el tipo.
        creds = cast(Credentials, flow.run_local_server(port=0))

    RUTA_TOKEN.parent.mkdir(parents=True, exist_ok=True)
    RUTA_TOKEN.write_text(creds.to_json())
    return creds


def _servicio():
    return build("calendar", "v3", credentials=_credenciales(), cache_discovery=False)


# Lee una fecha ISO 8601. Si no trae zona, asume ZONA_HORARIA.
# Falla con ValueError si el texto no es una fecha válida (el LLM puede mandar cualquier cosa).
def _parsear(valor: str) -> datetime:
    try:
        fecha = datetime.fromisoformat(valor)
    except ValueError:
        raise ValueError(f"fecha inválida, debe ir en formato ISO 8601: {valor!r}") from None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=ZoneInfo(ZONA_HORARIA))
    return fecha


# Fecha en el formato que pide Google (RFC 3339).
def _a_rfc3339(valor: str) -> str:
    return _parsear(valor).isoformat()


# Devuelve los eventos entre dos fechas, con las mismas claves que el stub (titulo, inicio, fin).
def listar_eventos(desde: str, hasta: str) -> list[dict]:
    # Se validan las fechas antes de armar el servicio: una fecha mala no debe disparar el OAuth.
    desde_google = _a_rfc3339(desde)
    hasta_google = _a_rfc3339(hasta)
    respuesta = (
        _servicio()
        .events()
        .list(
            calendarId="primary",
            timeMin=desde_google,
            timeMax=hasta_google,
            singleEvents=True,  # separa los eventos repetidos en ocurrencias individuales
            orderBy="startTime",
            maxResults=MAX_EVENTOS,
        )
        .execute()
    )
    eventos = []
    for e in respuesta.get("items", []):
        # Los eventos de todo el día traen "date" en vez de "dateTime".
        eventos.append(
            {
                "titulo": e.get("summary", "(sin título)"),
                "inicio": e["start"].get("dateTime") or e["start"].get("date"),
                "fin": e["end"].get("dateTime") or e["end"].get("date"),
            }
        )
    return eventos


# Crea un evento en el calendario principal y devuelve una frase corta, lista para decir en voz alta.
# Ojo: esta función SÍ escribe en el calendario. El agente nunca la llama directo: solo se ejecuta
# desde confirmacion.resolver(), después de que el usuario dijo "sí" (ver docs/seguridad.md).
def crear_evento_calendario(titulo: str, inicio: str, fin: str) -> str:
    titulo = titulo.strip()
    if not titulo:
        raise ValueError("el título no puede estar vacío")
    if len(titulo) > MAX_CHARS_TITULO:
        raise ValueError(f"el título es demasiado largo (máximo {MAX_CHARS_TITULO} caracteres)")

    desde = _parsear(inicio)
    hasta = _parsear(fin)
    if hasta <= desde:
        raise ValueError("fin debe ser posterior a inicio")

    _servicio().events().insert(
        calendarId="primary",
        body={
            "summary": titulo,
            "start": {"dateTime": desde.isoformat(), "timeZone": ZONA_HORARIA},
            "end": {"dateTime": hasta.isoformat(), "timeZone": ZONA_HORARIA},
        },
    ).execute()
    return f"Listo, creé el evento {titulo} el {desde:%d/%m} a las {desde:%H:%M}."


# Para autorizar a mano la primera vez (abre el navegador): python -m src.herramientas.calendario
if __name__ == "__main__":
    _credenciales()
    print(f"Autorizado. Token guardado en {RUTA_TOKEN}")
