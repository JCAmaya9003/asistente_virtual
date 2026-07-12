"""El control de calidad de las muestras. Un dataset malo produce un wake word que
'a veces' funciona, y eso es peor que uno que no funciona. Se valida al grabar.
"""
from __future__ import annotations

import math

from wakeword.calidad import duracion_de_voz, evaluar, pico, rms

SR = 16000


def tono(amplitud: float, segundos: float = 2.0, sr: int = SR) -> list[float]:
    n = int(segundos * sr)
    return [amplitud * math.sin(2 * math.pi * 200 * i / sr) for i in range(n)]


def test_muestra_buena_pasa() -> None:
    ok, motivo = evaluar(tono(0.4), SR)
    assert ok, motivo


def test_saturada_se_descarta() -> None:
    ok, motivo = evaluar(tono(1.0), SR)
    assert not ok and "saturada" in motivo


def test_muda_se_descarta() -> None:
    ok, motivo = evaluar([0.0] * (2 * SR), SR)
    assert not ok


def test_casi_inaudible_se_descarta() -> None:
    ok, motivo = evaluar(tono(0.01), SR)
    assert not ok


def test_voz_muy_corta_se_descarta() -> None:
    """Hablaste tarde y el nombre quedó cortado: 0.1s de voz en 2s de grabación."""
    audio = tono(0.5, segundos=0.1) + [0.0] * int(1.9 * SR)
    ok, motivo = evaluar(audio, SR)
    assert not ok and "no detecté" in motivo


def test_audio_vacio_se_descarta() -> None:
    ok, _ = evaluar([], SR)
    assert not ok


def test_pico_y_rms() -> None:
    assert pico([0.1, -0.9, 0.3]) == 0.9
    assert rms([0.0, 0.0]) == 0.0


def test_duracion_de_voz() -> None:
    audio = [0.5] * SR + [0.0] * SR          # 1 segundo de voz, 1 de silencio
    assert abs(duracion_de_voz(audio, SR) - 1.0) < 0.01
