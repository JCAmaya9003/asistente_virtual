"""La resolución de alias es lo que permite decir 'google' o 'chrome' para la misma app."""
from __future__ import annotations

import pytest

from skills.abrir_app import indice_de_alias, normalizar, resolver

APPS = {
    "chrome": {"alias": ["google", "navegador"], "destino": r"C:\chrome.exe"},
    "whatsapp": {"alias": ["wasap"], "destino": "whatsapp://"},
    "spotify": r"C:\spotify.exe",          # formato simple, sin alias
}


@pytest.fixture(scope="module")
def indice() -> dict[str, str]:
    return indice_de_alias(APPS)


@pytest.mark.parametrize("pedido", ["chrome", "google", "navegador", "GOOGLE", "Chrome"])
def test_todos_los_alias_abren_la_misma_app(indice, pedido: str) -> None:
    assert resolver(pedido, indice) == r"C:\chrome.exe"


def test_formato_simple_sigue_funcionando(indice) -> None:
    """No debe romper las configuraciones viejas (nombre: ruta)."""
    assert resolver("spotify", indice) == r"C:\spotify.exe"


def test_destino_puede_ser_un_protocolo(indice) -> None:
    assert resolver("wasap", indice) == "whatsapp://"


def test_normaliza_acentos() -> None:
    assert normalizar("Música") == "musica"


def test_tolera_basura_del_stt(indice) -> None:
    """Whisper puede agregar palabras: 'chrome por favor' debe seguir resolviendo."""
    assert resolver("chrome por favor", indice) == r"C:\chrome.exe"


def test_app_desconocida_no_resuelve(indice) -> None:
    assert resolver("photoshop", indice) is None


def test_pedido_vacio_no_resuelve(indice) -> None:
    assert resolver("   ", indice) is None


def test_gana_el_alias_mas_largo() -> None:
    """'google chrome' es más específico que 'google': debe ganar el más largo."""
    apps = {
        "a": {"alias": ["google"], "destino": "A"},
        "b": {"alias": ["google chrome"], "destino": "B"},
    }
    assert resolver("google chrome", indice_de_alias(apps)) == "B"
