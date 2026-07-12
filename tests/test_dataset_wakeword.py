"""El dataset del wake word. La ventana de 2s con desplazamiento aleatorio es lo que
permite que el detector funcione con la ventana deslizante de openWakeWord.
"""
from __future__ import annotations

import numpy as np

from wakeword.dataset import VENTANA, a_int16, aumentar, encajar


def test_audio_corto_se_rellena_a_dos_segundos() -> None:
    rng = np.random.default_rng(0)
    corto = np.ones(8000, dtype=np.float32) * 0.5      # 0.5 s
    assert len(encajar(corto, rng)) == VENTANA


def test_audio_largo_se_recorta_a_dos_segundos() -> None:
    rng = np.random.default_rng(0)
    largo = np.ones(80000, dtype=np.float32) * 0.5     # 5 s
    assert len(encajar(largo, rng)) == VENTANA


def test_el_desplazamiento_es_aleatorio() -> None:
    """Sin esto, el detector solo funciona si hablás justo a tiempo."""
    rng = np.random.default_rng(0)
    corto = np.ones(4000, dtype=np.float32)
    posiciones = {int(np.argmax(encajar(corto, rng) > 0.5)) for _ in range(20)}
    assert len(posiciones) > 1, "la palabra siempre cae en el mismo lugar"


def test_la_señal_sobrevive_al_relleno() -> None:
    rng = np.random.default_rng(0)
    corto = np.ones(4000, dtype=np.float32) * 0.7
    v = encajar(corto, rng)
    assert np.isclose(v.max(), 0.7)
    assert (v == 0).sum() == VENTANA - 4000            # el resto es silencio


def test_aumentar_no_satura() -> None:
    rng = np.random.default_rng(0)
    audio = np.ones(1000, dtype=np.float32) * 0.9
    assert np.abs(aumentar(audio, rng)).max() <= 1.0


def test_a_int16_respeta_el_rango() -> None:
    x = a_int16(np.array([-2.0, -1.0, 0.0, 1.0, 2.0], dtype=np.float32))
    assert x.dtype == np.int16
    assert x.min() >= -32767 and x.max() <= 32767
