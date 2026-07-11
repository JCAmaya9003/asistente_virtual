"""Salida por voz (TTS). Se implementa en v1 con Piper detrás de esta interfaz.
El motor es intercambiable sin tocar el núcleo (ver ADR 1 y §7.1 del ARCHITECTURE.md).
"""
from __future__ import annotations

from typing import Iterator, Protocol


class TTSEngine(Protocol):
    def hablar(self, texto: str) -> Iterator[bytes]: ...


class SalidaTTS:
    def __init__(self, engine: "TTSEngine | None" = None) -> None:
        self._engine = engine

    def decir(self, texto: str) -> None:
        # v1: enchufar Piper aquí.
        raise NotImplementedError("La salida por voz llega en la v1.")
