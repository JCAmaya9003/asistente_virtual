"""Hotkey global (hold-to-talk). Funciona aunque la ventana no tenga el foco.

pynput y NO la librería 'keyboard': esta última a veces exige privilegios de
administrador, y una de las reglas del proyecto es nunca correr elevados.

Mantener presionada la tecla = grabar. Soltarla = terminar. El usuario controla el fin
de la frase, en vez de depender de un umbral de silencio.
"""
from __future__ import annotations

import threading
from typing import Callable


def parsear_tecla(nombre: str):
    """Traduce el nombre de la config a un objeto de pynput. Import perezoso."""
    from pynput import keyboard

    nombre = (nombre or "").strip().lower()
    especiales = {
        "ctrl_r": keyboard.Key.ctrl_r,
        "ctrl_l": keyboard.Key.ctrl_l,
        "alt_r": keyboard.Key.alt_r,
        "alt_l": keyboard.Key.alt_l,
        "shift_r": keyboard.Key.shift_r,
        "shift_l": keyboard.Key.shift_l,
        "space": keyboard.Key.space,
        "f9": keyboard.Key.f9,
        "f10": keyboard.Key.f10,
        "pause": keyboard.Key.pause,
        "scroll_lock": keyboard.Key.scroll_lock,
    }
    if nombre in especiales:
        return especiales[nombre]
    if len(nombre) == 1:
        return keyboard.KeyCode.from_char(nombre)
    raise ValueError(f"tecla no reconocida: {nombre!r}")


class HoldToTalk:
    """Llama a on_press al presionar la tecla y a on_release al soltarla."""

    def __init__(self, tecla: str, on_press: Callable[[], None],
                 on_release: Callable[[], None]) -> None:
        self._nombre = tecla
        self._on_press = on_press
        self._on_release = on_release
        self._presionada = threading.Event()
        self._listener = None

    def iniciar(self) -> None:
        from pynput import keyboard

        objetivo = parsear_tecla(self._nombre)

        def press(tecla):
            if tecla == objetivo and not self._presionada.is_set():
                self._presionada.set()
                self._on_press()

        def release(tecla):
            if tecla == objetivo and self._presionada.is_set():
                self._presionada.clear()
                self._on_release()

        self._listener = keyboard.Listener(on_press=press, on_release=release)
        self._listener.daemon = True
        self._listener.start()

    def detener(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    @property
    def presionada(self) -> bool:
        return self._presionada.is_set()
