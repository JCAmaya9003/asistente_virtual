"""Genera muestras sintéticas del wake word con Piper, en Windows, sin Docker.

POR QUÉ NO USAMOS piper-sample-generator
----------------------------------------
Ese proyecto tiene un generador multi-hablante que mezcla speaker embeddings para
producir cientos de voces distintas... pero es SOLO INGLÉS. Para español se limita a usar
voces normales de Piper, que es exactamente lo que hacemos acá — y Piper ya está instalado
en el .venv del proyecto.

Además, su versión actual exige PyTorch 2, que choca con el PyTorch 1.13 que necesita el
entrenamiento de openWakeWord. Eliminarlo resuelve el conflicto.

CÓMO SE LOGRA VARIEDAD
----------------------
Un dataset donde todas las muestras suenan igual produce un detector frágil. Variamos:
  - VOZ: varias voces en español (distinto timbre, acento y género).
  - VELOCIDAD (length_scale): de pausado a apurado.
  - EXPRESIVIDAD (noise_scale): cuánta variación prosódica.
  - RITMO (noise_w_scale): variación en la duración de los fonemas.
  - VOLUMEN.

Aun así, estas voces hablan con acento neutro de locutor. Por eso TUS grabaciones reales
(wakeword/muestras/positivas/) siguen siendo imprescindibles.
"""
from __future__ import annotations

import itertools
import wave
from pathlib import Path

# Rejilla de parámetros. El producto cartesiano de estos con las voces da la variedad.
LENGTH_SCALES = (0.85, 1.0, 1.15, 1.3)      # velocidad: <1 rápido, >1 lento
NOISE_SCALES = (0.5, 0.667, 0.8)            # expresividad de la prosodia
NOISE_W_SCALES = (0.6, 0.8, 1.0)            # variación en la duración de fonemas
VOLUMENES = (0.7, 0.85, 1.0)


def combinaciones(voces: list[str], objetivo: int) -> list[tuple]:
    """Reparte 'objetivo' muestras entre todas las combinaciones posibles.

    Es determinista y equilibrado: cada voz recibe la misma cantidad de variantes, y las
    variantes cubren la rejilla de forma pareja en vez de al azar.
    """
    rejilla = list(itertools.product(voces, LENGTH_SCALES, NOISE_SCALES,
                                     NOISE_W_SCALES, VOLUMENES))
    if not rejilla:
        return []
    # Repite la rejilla en ciclo hasta llegar al objetivo.
    return [rejilla[i % len(rejilla)] for i in range(objetivo)]


def generar(frases: list[str], voces: list[str], salida: Path,
            objetivo: int = 2000, verbose: bool = True) -> int:
    """Sintetiza 'objetivo' muestras variando voz y parámetros. Devuelve cuántas escribió."""
    from piper import PiperVoice, SynthesisConfig

    salida.mkdir(parents=True, exist_ok=True)
    cargadas = {}
    for ruta in voces:
        if not Path(ruta).exists():
            if verbose:
                print(f"  [!] falta la voz: {ruta}")
            continue
        cargadas[ruta] = PiperVoice.load(ruta)

    if not cargadas:
        raise RuntimeError("no hay ninguna voz de Piper disponible")

    combos = combinaciones(list(cargadas.keys()), objetivo)
    escritas = 0

    for i, (voz, length, noise, noise_w, vol) in enumerate(combos):
        frase = frases[i % len(frases)]      # alterna entre las variantes del nombre
        cfg = SynthesisConfig(
            length_scale=length, noise_scale=noise,
            noise_w_scale=noise_w, volume=vol,
        )
        destino = salida / f"{i:05d}.wav"
        with wave.open(str(destino), "wb") as w:
            cargadas[voz].synthesize_wav(frase, w, syn_config=cfg)
        escritas += 1

        if verbose and escritas % 200 == 0:
            print(f"  {escritas}/{objetivo}...")

    return escritas
