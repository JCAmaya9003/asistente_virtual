"""Entrada por voz (push-to-talk → faster-whisper). Se implementa en v2.
La interfaz es idéntica a EntradaCLI: el núcleo no distingue la fuente.
"""
from __future__ import annotations


class EntradaVoz:
    def leer(self) -> str | None:
        # v2: capturar audio (sounddevice), transcribir (faster-whisper, CUDA),
        # devolver el texto. El buffer vive en RAM y se descarta tras transcribir.
        raise NotImplementedError("La entrada por voz llega en la v2.")
