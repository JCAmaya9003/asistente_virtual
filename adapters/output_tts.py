"""Salida por voz (TTS). Reproduce el audio WAV que sintetiza un motor (Piper por defecto).
El motor es intercambiable; esta clase solo se ocupa de la reproducción por plataforma.
"""
from __future__ import annotations

import sys
from typing import Protocol


class TTSEngine(Protocol):
    def sintetizar_wav(self, texto: str) -> bytes: ...


class SalidaTTS:
    def __init__(self, engine: "TTSEngine", tambien_consola: bool = True) -> None:
        self._engine = engine
        self._tambien_consola = tambien_consola

    def decir(self, texto: str) -> None:
        if self._tambien_consola:
            print(f"asistente> {texto}")
        wav = self._engine.sintetizar_wav(texto)
        self._reproducir(wav)

    @staticmethod
    def _reproducir(wav: bytes) -> None:
        if sys.platform == "win32":
            import winsound
            # SND_MEMORY reproduce el WAV desde RAM; bloquea hasta terminar de hablar.
            winsound.PlaySound(wav, winsound.SND_MEMORY)
        else:
            # Fuera de Windows la reproducción se unifica con sounddevice en la v2.
            raise NotImplementedError("Reproducción de audio: Windows en la v1.")