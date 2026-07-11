"""Lógica del oído, testeada SIN micrófono ni GPU (principio del ROADMAP: ninguna prueba
del núcleo toca hardware de audio).
"""
from __future__ import annotations

import pytest

from adapters.input_voice import es_silencio, rms
from adapters.stt_whisper import (construir_initial_prompt, limpiar_transcripcion, resolver_dispositivo)


# --- resolución de dispositivo ---

def test_auto_usa_cuda_si_hay() -> None:
    assert resolver_dispositivo("auto", "auto", True) == ("cuda", "int8_float16")


def test_auto_cae_a_cpu_sin_cuda() -> None:
    assert resolver_dispositivo("auto", "auto", False) == ("cpu", "int8")


def test_cpu_explicito_ignora_cuda() -> None:
    assert resolver_dispositivo("cpu", "auto", True) == ("cpu", "int8")


def test_compute_type_explicito_se_respeta() -> None:
    assert resolver_dispositivo("cuda", "float16", True) == ("cuda", "float16")


# --- initial_prompt: sesga a Whisper hacia los nombres de apps ---

def test_initial_prompt_incluye_las_apps() -> None:
    prompt = construir_initial_prompt(["spotify", "chrome"])
    assert "Spotify" in prompt and "Chrome" in prompt


def test_initial_prompt_vacio_sin_apps() -> None:
    assert construir_initial_prompt([]) == ""


# --- limpieza de la transcripción de Whisper ---

@pytest.mark.parametrize("crudo,esperado", [
    ("  ¿Qué hora es?  ", "Qué hora es"),
    ("Abre Spotify.", "Abre Spotify"),
    ("hola   mundo", "hola mundo"),
    ("", ""),
])
def test_limpiar_transcripcion(crudo: str, esperado: str) -> None:
    assert limpiar_transcripcion(crudo) == esperado


def test_transcripcion_limpia_enruta_bien() -> None:
    """El texto de Whisper debe poder entrar al router tal cual."""
    from core.registry import cargar_skills
    from core.router import Router

    router = Router(cargar_skills())
    texto = limpiar_transcripcion(" ¿Qué hora es? ").lower()
    intencion = router.enrutar(texto)
    assert intencion is not None and intencion.skill == "hora"


# --- detección de silencio (endpointing) ---

def test_rms_de_silencio_es_cero() -> None:
    assert rms([0.0] * 100) == 0.0


def test_silencio_detectado() -> None:
    assert es_silencio([0.001] * 100, umbral=0.015)


def test_habla_no_es_silencio() -> None:
    assert not es_silencio([0.5, -0.4, 0.6] * 30, umbral=0.015)


def test_bloque_vacio_es_silencio() -> None:
    assert es_silencio([], umbral=0.015)
