"""Entrada por voz: push-to-talk. Misma interfaz que EntradaCLI, así el núcleo no
distingue la fuente (§3 del ARCHITECTURE.md).

Flujo: Enter → graba → detecta el fin del habla por silencio → transcribe → devuelve texto.

Push-to-talk deliberadamente, NO wake word (ADR 6): evita VAD siempre activo, ruido
ambiente y falsos positivos, que son un proyecto entero aparte (v4).
El buffer de audio vive en RAM y se descarta al terminar.
"""
from __future__ import annotations

import math


# --------------------------------------------------------------------------- #
# Funciones puras (testeables sin micrófono)
# --------------------------------------------------------------------------- #

def rms(bloque) -> float:
    """Energía del bloque de audio. Sirve como detector de silencio barato."""
    if len(bloque) == 0:
        return 0.0
    suma = sum(float(x) * float(x) for x in bloque)
    return math.sqrt(suma / len(bloque))


def es_silencio(bloque, umbral: float) -> bool:
    return rms(bloque) < umbral


# --------------------------------------------------------------------------- #
# Captura
# --------------------------------------------------------------------------- #

class EntradaVoz:
    def __init__(self, engine, sample_rate: int = 16000, bloque_ms: int = 100,
                 silencio_ms: int = 1200, umbral_silencio: float = 0.015,
                 max_segundos: int = 15, min_segundos: float = 0.4) -> None:
        self._engine = engine
        self._sr = sample_rate
        self._bloque = int(sample_rate * bloque_ms / 1000)
        self._bloques_silencio = max(1, silencio_ms // bloque_ms)
        self._umbral = umbral_silencio
        self._max_bloques = int(max_segundos * 1000 / bloque_ms)
        self._min_bloques = int(min_segundos * 1000 / bloque_ms)

    def leer(self) -> str | None:
        try:
            orden = input("[Enter para hablar, o escribí 'salir'] ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if orden:                       # permite escribir en vez de hablar (útil para depurar)
            return orden

        audio = self._grabar()
        if audio is None or len(audio) < self._min_bloques * self._bloque:
            print("[No escuché nada.]")
            return ""
        texto = self._engine.transcribir(audio)
        print(f"[oí]: {texto or '(nada)'}")
        return texto

    def _grabar(self):
        import numpy as np
        import sounddevice as sd

        print("Hablá... ", end="", flush=True)
        bloques: list = []
        silencios_seguidos = 0

        with sd.InputStream(samplerate=self._sr, channels=1, dtype="float32",
                            blocksize=self._bloque) as stream:
            for i in range(self._max_bloques):
                datos, _ = stream.read(self._bloque)
                bloque = datos[:, 0].copy()
                bloques.append(bloque)

                if es_silencio(bloque, self._umbral):
                    silencios_seguidos += 1
                else:
                    silencios_seguidos = 0

                # Corta tras N bloques de silencio, pero solo si ya hubo habla.
                if (silencios_seguidos >= self._bloques_silencio
                        and i >= self._min_bloques):
                    break

        print("listo.")
        if not bloques:
            return None
        return np.concatenate(bloques)


# --------------------------------------------------------------------------- #
# Grabación continua (v3): el stream queda abierto y el hotkey marca los bordes
# --------------------------------------------------------------------------- #

class GrabadorContinuo:
    """Mantiene el InputStream abierto y acumula audio solo entre empezar() y terminar().

    El stream abierto permanentemente es lo que permite al watchdog verificar la salud
    del micrófono sin interferir con la grabación.
    """

    def __init__(self, sample_rate: int = 16000, bloque_ms: int = 100,
                 max_segundos: int = 30) -> None:
        self._sr = sample_rate
        self._bloque = int(sample_rate * bloque_ms / 1000)
        self._max_bloques = int(max_segundos * 1000 / bloque_ms)
        self._stream = None
        self._buffer: list = []
        self._grabando = False
        self._ultimo = None
        self.on_frame = None          # (v4) callback del detector de wake word

    def abrir(self) -> None:
        import numpy as np
        import sounddevice as sd

        def callback(indata, frames, tiempo, status):
            bloque = indata[:, 0].copy()
            self._ultimo = bloque                     # lo leen el watchdog y el endpointer
            if self._grabando and len(self._buffer) < self._max_bloques:
                self._buffer.append(bloque)
            if self.on_frame is not None:
                # openWakeWord espera int16, no float32.
                self.on_frame((np.clip(bloque, -1.0, 1.0) * 32767).astype(np.int16))

        self._stream = sd.InputStream(
            samplerate=self._sr, channels=1, dtype="float32",
            blocksize=self._bloque, callback=callback,
        )
        self._stream.start()

    def ultimo_bloque(self):
        """Último bloque capturado. Lo usa el endpointer por silencio del daemon."""
        return self._ultimo

    def cerrar(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def reabrir(self) -> None:
        self.cerrar()
        self.abrir()

    def esta_sano(self) -> bool:
        """False si el stream entrega ceros (dispositivo desconectado o dormido).

        Silencio real tiene ruido de fondo: varianza pequeña pero > 0. Un stream muerto
        entrega ceros exactos.
        """
        from core.watchdog import microfono_mudo

        if self._stream is None or self._ultimo is None:
            return False
        return not microfono_mudo(self._ultimo)

    def empezar(self) -> None:
        self._buffer = []
        self._grabando = True

    def terminar(self):
        import numpy as np

        self._grabando = False
        if not self._buffer:
            return None
        audio = np.concatenate(self._buffer)
        self._buffer = []
        return audio
