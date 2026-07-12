"""Estados de residencia: el asistente corre 24/7 pero pasa el 99% del tiempo sin tocar
la GPU (§2.4 del ARCHITECTURE.md).

    DORMIDO  →  DESPERTANDO  →  ACTIVO  →  ENFRIANDO  →  DORMIDO
    (wake word)  (warm-up)      (comando)  (5 min)

EL TRUCO DEL WARM-UP ESPECULATIVO
---------------------------------
El usuario tarda 1-3 segundos en decir el comando después del wake word. Esa es la
ventana de carga, y es GRATIS. Al disparar el wake word se empieza a cargar Whisper
ANTES de saber qué va a decir. Cuando termina de hablar, el modelo ya está caliente.

El cold start no desaparece: se esconde detrás de la propia voz del usuario.
"""
from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Callable


class Estado(Enum):
    DORMIDO = "dormido"
    DESPERTANDO = "despertando"
    ACTIVO = "activo"
    ENFRIANDO = "enfriando"


class Residencia:
    def __init__(self, cargar: Callable[[], object], descargar: Callable[[], None],
                 gracia_s: float = 300.0) -> None:
        self._cargar = cargar            # sube Whisper a la GPU (lento la 1ª vez)
        self._descargar = descargar      # lo libera
        self._gracia = gracia_s

        self.estado = Estado.DORMIDO
        self._recurso = None
        self._lock = threading.Lock()
        self._hilo_carga: threading.Thread | None = None
        self._timer: threading.Timer | None = None

    # --- warm-up especulativo ---------------------------------------------
    def despertar(self) -> None:
        """Se llama EN CUANTO dispara el wake word, sin esperar al comando.
        Arranca la carga en un hilo aparte: mientras el usuario habla, el modelo sube.
        """
        with self._lock:
            if self._timer is not None:          # estaba enfriando: cancelar y reusar
                self._timer.cancel()
                self._timer = None
            if self.estado in (Estado.ACTIVO, Estado.ENFRIANDO) and self._recurso:
                self.estado = Estado.ACTIVO
                return
            if self.estado == Estado.DESPERTANDO:
                return
            self.estado = Estado.DESPERTANDO

        self._hilo_carga = threading.Thread(target=self._cargar_ahora, daemon=True)
        self._hilo_carga.start()

    def _cargar_ahora(self) -> None:
        recurso = self._cargar()
        with self._lock:
            self._recurso = recurso
            self.estado = Estado.ACTIVO

    def obtener(self, timeout_s: float = 30.0):
        """Devuelve el recurso, esperando a que termine el warm-up si hace falta.
        En el caso normal ya está listo: el usuario tardó más en hablar que el modelo
        en cargar.
        """
        if self._hilo_carga is not None:
            self._hilo_carga.join(timeout=timeout_s)
        with self._lock:
            if self._recurso is None:
                raise RuntimeError("el modelo no cargó a tiempo")
            self.estado = Estado.ACTIVO
            return self._recurso

    # --- enfriado ----------------------------------------------------------
    def enfriar(self) -> None:
        """Se llama al terminar de atender un comando. Arranca la cuenta de gracia:
        si hablás de nuevo dentro de la ventana, ni te enterás."""
        with self._lock:
            if self._recurso is None:
                return
            self.estado = Estado.ENFRIANDO
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._gracia, self._dormir)
            self._timer.daemon = True
            self._timer.start()

    def _dormir(self) -> None:
        with self._lock:
            self._recurso = None
            self._hilo_carga = None
            self._timer = None
            self.estado = Estado.DORMIDO
        try:
            self._descargar()
        except Exception:
            pass

    def detener(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        self._dormir()
