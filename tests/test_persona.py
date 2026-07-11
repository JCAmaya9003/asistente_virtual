"""La capa de persona normaliza el texto para el TTS y aplica el perfil de estilo."""
from __future__ import annotations

from core.persona import Persona


def test_agrega_puntuacion_final() -> None:
    p = Persona({"tono": "neutral"})
    assert p.estilizar("son las tres") == "son las tres."


def test_neutral_no_agrega_muletillas() -> None:
    p = Persona({"tono": "neutral", "muletillas": ["che", "mirá"]})
    assert p.estilizar("abriendo spotify") == "abriendo spotify."


def test_casual_agrega_una_muletilla_configurada() -> None:
    muletillas = ["che", "mirá"]
    p = Persona({"tono": "casual", "muletillas": muletillas})
    salida = p.estilizar("son las tres")
    assert "son las tres" in salida
    assert any(salida.startswith(m + ",") for m in muletillas)


def test_colapsa_espacios() -> None:
    p = Persona({"tono": "neutral"})
    assert p.estilizar("hola    mundo\n\n  test") == "hola mundo test."


def test_texto_vacio() -> None:
    assert Persona({}).estilizar("   ") == ""