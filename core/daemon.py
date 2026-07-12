"""Modo residente: el asistente vive en la bandeja.

Dos formas de invocarlo, y conviven:
  - Wake word ("Raftalia")  → si hay modelo entrenado.
  - Hotkey global (hold)    → siempre, como respaldo.

Piezas:
  - DetectorWakeWord → corre siempre en CPU, ~200 KB, cero VRAM.
  - Residencia       → Whisper solo vive en la GPU cuando hace falta (warm-up especulativo).
  - Watchdog         → detecta el micrófono mudo y reabre el stream.
  - Bandeja          → el usuario ve y controla cuándo se escucha.

El núcleo (router, compuerta, skills) es exactamente el mismo del REPL.
"""
from __future__ import annotations

import threading
import time


class Daemon:
    def __init__(self, *, construir_stt, grabador, procesar, salida, auditor,
                 tecla: str = "ctrl_r", nombre: str = "Asistente",
                 wakeword=None, gracia_s: float = 300.0,
                 silencio_ms: int = 1200, umbral_silencio: float = 0.015,
                 max_segundos: int = 15) -> None:
        from core.residencia import Residencia

        self._grabador = grabador
        self._procesar = procesar
        self._salida = salida
        self._auditor = auditor
        self._tecla = tecla
        self._nombre = nombre
        self._detector = wakeword          # None = solo hotkey

        # Whisper solo ocupa VRAM cuando hace falta.
        self._residencia = Residencia(construir_stt, self._liberar_stt, gracia_s=gracia_s)

        self._bloques_silencio = max(1, silencio_ms // 100)
        self._umbral_silencio = umbral_silencio
        self._max_segundos = max_segundos

        self._escuchando = True
        self._ocupado = threading.Lock()
        self._parar = threading.Event()
        self._hotkey = None
        self._bandeja = None
        self._watchdog = None

    # --- ciclo de vida -----------------------------------------------------
    def correr(self) -> None:
        from adapters.hotkey import HoldToTalk
        from adapters.tray import Bandeja
        from core.watchdog import Watchdog

        self._grabador.abrir()

        self._hotkey = HoldToTalk(self._tecla, self._empezar, self._terminar)
        self._hotkey.iniciar()

        self._bandeja = Bandeja(self._nombre, self._toggle, self.detener)
        self._bandeja.iniciar()

        self._watchdog = Watchdog(
            comprobar=self._grabador.esta_sano,
            reparar=self._grabador.reabrir,
            latir=self._auditor.latido,
        )
        self._watchdog.iniciar()

        if self._detector is not None:
            self._grabador.on_frame = self._escuchar_wakeword
            print(f"[{self._nombre}] activo. Decí «{self._nombre}» o mantené «{self._tecla}».")
        else:
            print(f"[{self._nombre}] activo en la bandeja. "
                  f"Mantené «{self._tecla}» para hablar. (Sin wake word entrenado.)")

        try:
            while not self._parar.is_set():
                time.sleep(0.2)
        except KeyboardInterrupt:
            pass
        finally:
            self._cerrar()

    def detener(self) -> None:
        self._parar.set()

    def _cerrar(self) -> None:
        for c in (self._watchdog, self._hotkey, self._bandeja, self._residencia):
            if c is not None:
                try:
                    c.detener()
                except Exception:
                    pass
        self._grabador.cerrar()

    def _liberar_stt(self) -> None:
        print("[residencia] libero la VRAM.")

    # --- wake word ---------------------------------------------------------
    def _escuchar_wakeword(self, frame_int16) -> None:
        """Lo llama el grabador con cada frame. Corre en el hilo de audio: tiene que ser
        rápido y NUNCA bloquear."""
        if not self._escuchando or self._ocupado.locked():
            return
        try:
            if self._detector.procesar(frame_int16, time.monotonic()):
                threading.Thread(target=self._atender_wakeword, daemon=True).start()
        except Exception as e:
            print(f"[wakeword] error: {e}")

    def _atender_wakeword(self) -> None:
        if not self._ocupado.acquire(blocking=False):
            return
        try:
            # WARM-UP ESPECULATIVO: Whisper empieza a cargar AHORA, mientras el usuario
            # todavía está diciendo el comando. Cuando termine, ya está caliente.
            self._residencia.despertar()
            self._salida.decir("¿Sí?")

            audio = self._grabar_hasta_silencio()
            if audio is None or len(audio) == 0:
                print("○ no escuché nada.")
                return
            self._responder(audio)
        finally:
            self._detector.reset()
            self._residencia.enfriar()
            self._ocupado.release()

    def _grabar_hasta_silencio(self):
        from adapters.input_voice import es_silencio

        self._grabador.empezar()
        silencios = 0
        limite = int(self._max_segundos * 10)      # bloques de 100 ms

        for i in range(limite):
            time.sleep(0.1)
            bloque = self._grabador.ultimo_bloque()
            if bloque is None:
                continue
            if es_silencio(bloque, self._umbral_silencio):
                silencios += 1
            else:
                silencios = 0
            if silencios >= self._bloques_silencio and i > 5:
                break

        return self._grabador.terminar()

    # --- hotkey ------------------------------------------------------------
    def _toggle(self, escuchando: bool) -> None:
        self._escuchando = escuchando
        print(f"[{self._nombre}] {'escuchando' if escuchando else 'en pausa'}.")

    def _empezar(self) -> None:
        if not self._escuchando or self._ocupado.locked():
            return
        self._residencia.despertar()               # warm-up también en el hotkey
        self._grabador.empezar()
        print("● grabando...", flush=True)

    def _terminar(self) -> None:
        if not self._escuchando:
            return
        audio = self._grabador.terminar()
        if audio is None or len(audio) == 0:
            print("○ no escuché nada.")
            self._residencia.enfriar()
            return
        threading.Thread(target=self._responder_y_enfriar, args=(audio,),
                         daemon=True).start()

    def _responder_y_enfriar(self, audio) -> None:
        if not self._ocupado.acquire(blocking=False):
            return
        try:
            self._responder(audio)
        finally:
            self._residencia.enfriar()
            self._ocupado.release()

    # --- común -------------------------------------------------------------
    def _responder(self, audio) -> None:
        try:
            stt = self._residencia.obtener()       # ya cargado gracias al warm-up
            texto = stt.transcribir(audio)
            if not texto:
                print("○ no entendí nada.")
                return
            print(f"[oí]: {texto}")
            respuesta = self._procesar(texto)
            if respuesta:
                self._salida.decir(respuesta)
        except Exception as e:
            print(f"[error al responder: {e}]")
