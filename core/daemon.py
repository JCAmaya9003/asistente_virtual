"""Modo residente: el asistente vive en la bandeja y responde al hotkey global.

Junta las tres piezas de la v3:
  - HoldToTalk  → mantener la tecla presionada graba; soltarla transcribe y ejecuta.
  - Bandeja     → el usuario ve y controla cuándo se escucha.
  - Watchdog    → detecta el micrófono mudo y reabre el stream.

El núcleo (router, compuerta, skills) es exactamente el mismo del REPL. El daemon es
otro adaptador de entrada: no sabe nada de skills.
"""
from __future__ import annotations

import threading
import time


class Daemon:
    def __init__(self, *, stt, grabador, procesar, salida, auditor,
                 tecla: str = "ctrl_r", nombre: str = "Asistente") -> None:
        self._stt = stt
        self._grabador = grabador          # GrabadorContinuo
        self._procesar = procesar          # (texto) -> respuesta hablada
        self._salida = salida
        self._auditor = auditor
        self._tecla = tecla
        self._nombre = nombre

        self._escuchando = True
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

        print(f"[{self._nombre}] activo en la bandeja. "
              f"Mantené «{self._tecla}» para hablar. Ctrl+C para salir.")
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
        for componente in (self._watchdog, self._hotkey, self._bandeja):
            if componente is not None:
                try:
                    componente.detener()
                except Exception:
                    pass
        self._grabador.cerrar()

    # --- eventos -----------------------------------------------------------
    def _toggle(self, escuchando: bool) -> None:
        self._escuchando = escuchando
        print(f"[{self._nombre}] {'escuchando' if escuchando else 'en pausa'}.")

    def _empezar(self) -> None:
        if not self._escuchando:
            return
        self._grabador.empezar()
        print("● grabando...", flush=True)

    def _terminar(self) -> None:
        if not self._escuchando:
            return
        audio = self._grabador.terminar()
        if audio is None or len(audio) == 0:
            print("○ no escuché nada.")
            return

        # El trabajo pesado va en un hilo aparte: el listener del hotkey nunca se bloquea.
        threading.Thread(target=self._responder, args=(audio,), daemon=True).start()

    def _responder(self, audio) -> None:
        try:
            texto = self._stt.transcribir(audio)
            if not texto:
                print("○ no entendí nada.")
                return
            print(f"[oí]: {texto}")
            respuesta = self._procesar(texto)
            if respuesta:
                self._salida.decir(respuesta)
        except Exception as e:
            print(f"[error al responder: {e}]")
