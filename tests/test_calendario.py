from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from src.herramientas import calendario


# Servicio de Google falso: ningún test llama a la API real ni abre el navegador.
# Guarda lo que recibió para poder revisarlo, y devuelve la respuesta que se le pida.
@pytest.fixture
def servicio(monkeypatch):
    falso = MagicMock()
    monkeypatch.setattr(calendario, "_servicio", lambda: falso)
    return falso


# --- Fechas -----------------------------------------------------------------


def test_fecha_sin_zona_se_interpreta_en_santiago():
    fecha = calendario._parsear("2026-11-09T17:00:00")
    assert fecha.tzinfo is not None
    # En noviembre Chile está en horario de verano: UTC-3
    assert fecha.utcoffset() == timedelta(hours=-3)


def test_fecha_con_zona_se_respeta():
    fecha = calendario._parsear("2026-11-09T17:00:00+00:00")
    assert fecha.utcoffset() == timedelta(0)


@pytest.mark.parametrize("valor", ["mañana", "", "2026-13-45", "hola"])
def test_fecha_invalida_falla_con_value_error(valor):
    with pytest.raises(ValueError, match="ISO 8601"):
        calendario._parsear(valor)


# --- listar_eventos ---------------------------------------------------------


def test_listar_eventos_traduce_la_respuesta_de_google(servicio):
    servicio.events().list().execute.return_value = {
        "items": [
            {
                "summary": "Clase",
                "start": {"dateTime": "2026-11-09T14:40:00-03:00"},
                "end": {"dateTime": "2026-11-09T16:50:00-03:00"},
            }
        ]
    }
    assert calendario.listar_eventos(
        "2026-11-09T00:00:00", "2026-11-10T00:00:00"
    ) == [
        {
            "titulo": "Clase",
            "inicio": "2026-11-09T14:40:00-03:00",
            "fin": "2026-11-09T16:50:00-03:00",
        }
    ]


def test_listar_eventos_acepta_eventos_de_todo_el_dia_y_sin_titulo(servicio):
    servicio.events().list().execute.return_value = {
        "items": [{"start": {"date": "2026-11-12"}, "end": {"date": "2026-11-13"}}]
    }
    assert calendario.listar_eventos("2026-11-12T00:00:00", "2026-11-13T00:00:00") == [
        {"titulo": "(sin título)", "inicio": "2026-11-12", "fin": "2026-11-13"}
    ]


def test_listar_eventos_sin_eventos_devuelve_lista_vacia(servicio):
    servicio.events().list().execute.return_value = {}
    assert calendario.listar_eventos("2026-11-09T00:00:00", "2026-11-10T00:00:00") == []


def test_listar_eventos_pide_a_google_lo_correcto(servicio):
    servicio.events().list().execute.return_value = {"items": []}
    servicio.reset_mock()
    calendario.listar_eventos("2026-11-09T00:00:00", "2026-11-10T00:00:00")
    kwargs = servicio.events().list.call_args.kwargs
    assert kwargs["calendarId"] == "primary"
    assert kwargs["timeMin"] == "2026-11-09T00:00:00-03:00"
    assert kwargs["timeMax"] == "2026-11-10T00:00:00-03:00"
    assert kwargs["singleEvents"] is True
    assert kwargs["maxResults"] == calendario.MAX_EVENTOS


def test_listar_eventos_con_fecha_invalida_no_llama_a_google(servicio):
    with pytest.raises(ValueError):
        calendario.listar_eventos("ayer", "2026-11-10T00:00:00")
    servicio.events.assert_not_called()


# --- crear_evento_calendario ------------------------------------------------


def test_crear_evento_envia_lo_correcto_y_responde_para_voz(servicio):
    respuesta = calendario.crear_evento_calendario(
        "Dentista", "2026-11-09T17:00:00", "2026-11-09T18:00:00"
    )
    kwargs = servicio.events().insert.call_args.kwargs
    assert kwargs["calendarId"] == "primary"
    assert kwargs["body"] == {
        "summary": "Dentista",
        "start": {"dateTime": "2026-11-09T17:00:00-03:00", "timeZone": "America/Santiago"},
        "end": {"dateTime": "2026-11-09T18:00:00-03:00", "timeZone": "America/Santiago"},
    }
    servicio.events().insert().execute.assert_called_once()
    assert respuesta == "Listo, creé el evento Dentista el 09/11 a las 17:00."


def test_crear_evento_recorta_espacios_del_titulo(servicio):
    calendario.crear_evento_calendario(
        "  Dentista  ", "2026-11-09T17:00:00", "2026-11-09T18:00:00"
    )
    assert servicio.events().insert.call_args.kwargs["body"]["summary"] == "Dentista"


@pytest.mark.parametrize(
    "titulo, inicio, fin, mensaje",
    [
        ("", "2026-11-09T17:00:00", "2026-11-09T18:00:00", "vacío"),
        ("   ", "2026-11-09T17:00:00", "2026-11-09T18:00:00", "vacío"),
        ("x" * 201, "2026-11-09T17:00:00", "2026-11-09T18:00:00", "demasiado largo"),
        ("Cita", "2026-11-09T18:00:00", "2026-11-09T17:00:00", "posterior"),
        ("Cita", "2026-11-09T17:00:00", "2026-11-09T17:00:00", "posterior"),
        ("Cita", "mañana", "2026-11-09T18:00:00", "ISO 8601"),
    ],
)
def test_crear_evento_invalido_falla_antes_de_tocar_el_calendario(
    servicio, titulo, inicio, fin, mensaje
):
    with pytest.raises(ValueError, match=mensaje):
        calendario.crear_evento_calendario(titulo, inicio, fin)
    servicio.events.assert_not_called()


def test_crear_evento_acepta_titulo_de_200_caracteres(servicio):
    calendario.crear_evento_calendario(
        "x" * 200, "2026-11-09T17:00:00", "2026-11-09T18:00:00"
    )
    servicio.events().insert().execute.assert_called_once()


def test_crear_evento_mezclando_con_y_sin_zona_se_compara_bien(servicio):
    # inicio sin zona (Santiago, -03:00) y fin con zona UTC: 17:00-03 = 20:00Z, así que 19:00Z es anterior
    with pytest.raises(ValueError, match="posterior"):
        calendario.crear_evento_calendario(
            "Cita", "2026-11-09T17:00:00", "2026-11-09T19:00:00+00:00"
        )


# --- Credenciales -----------------------------------------------------------


def test_sin_token_ni_client_id_falla_claro_sin_abrir_el_navegador(monkeypatch, tmp_path):
    monkeypatch.setattr(calendario, "RUTA_TOKEN", tmp_path / "no_existe" / "token.json")
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_ID"):
        calendario._credenciales()
