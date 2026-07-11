"""Watchdog de audio. Lo que mata a un asistente always-on NO es el consumo: es que
muere en silencio (§2.5 del ARCHITECTURE.md).

Fallas que cubre:
  - Cambia el dispositivo de audio (desconectás audífonos, se apaga el Bluetooth, Windows
    actualiza un driver). El stream entrega ceros SIN lanzar excepción.
  - Suspensión y reanudación de Windows. Mismo síntoma.

Detección: cada N segundos se verifica que estén entrando muestras con varianza != 0.
Si el micrófono está mudo, se reabre el stream. Cada latido queda en el audit log: si el
último es de hace tres días, sabés exactamente qué pasó.
"""
from __future__ import annotations

import math
import threading
import time
from typing import Callable


def varianza(muestras) -> float:
    """Varianza de las muestras. Un stream muerto entrega ceros: varianza exactamente 0.

    Se distingue de 'silencio real' (que tiene ruido de fondo, varianza pequeña pero > 0).
    """
    n = len(muestras)
    if n == 0:
        return 0.0
    media = sum(float(x) for x in muestras) / n
    return sum((float(x) - media) ** 2 for x in muestras) / n


def microfono_mudo(muestras, epsilon: float = 1e-9) -> bool:
    """True si el stream está entregando ceros (muerto), no si hay silencio real."""
    return varianza(muestras) < epsilon


class Watchdog:
    """Hilo en segundo plano que vigila el micrófono y late en el audit log."""

    def __init__(self, comprobar: Callable[[], bool], reparar: Callable[[], None],
                 latir: Callable[[], None] | None = None,
                 intervalo_s: int = 30, latido_cada_s: int = 300) -> None:
        self._comprobar = comprobar          # -> True si el micrófono está sano
        self._reparar = reparar              # reabre el stream
        self._latir = latir
        self._intervalo = intervalo_s
        self._latido_cada = latido_cada_s
        self._parar = threading.Event()
        self._hilo: threading.Thread | None = None
        self.fallos = 0

    def iniciar(self) -> None:
        self._hilo = threading.Thread(target=self._bucle, daemon=True, name="watchdog")
        self._hilo.start()

    def detener(self) -> None:
        self._parar.set()
        if self._hilo is not None:
            self._hilo.join(timeout=2)

    def _bucle(self) -> None:
        ultimo_latido = 0.0
        while not self._parar.wait(self._intervalo):
            try:
                if not self._comprobar():
                    self.fallos += 1
                    print("[watchdog] micrófono mudo; reabriendo el stream...")
                    self._reparar()
            except Exception as e:
                # El watchdog JAMÁS debe tumbar el proceso que vigila.
                print(f"[watchdog] error al comprobar: {e}")

            ahora = time.monotonic()
            if self._latir is not None and ahora - ultimo_latido >= self._latido_cada:
                try:
                    self._latir()
                    ultimo_latido = ahora
                except Exception:
                    pass
