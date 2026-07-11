"""Ícono de bandeja del sistema.

Windows 11 muestra el ícono de micrófono en la bandeja las 24 horas mientras el stream
esté abierto: no se puede evitar. Se convierte en feature — desde acá el usuario ve y
controla cuándo el asistente escucha (§2.5 del ARCHITECTURE.md).
"""
from __future__ import annotations

from typing import Callable


def _icono(color: tuple[int, int, int]):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (64, 64), (30, 30, 30))
    d = ImageDraw.Draw(img)
    d.ellipse((16, 8, 48, 40), fill=color)      # cápsula del micrófono
    d.rectangle((30, 40, 34, 52), fill=color)   # pie
    d.rectangle((22, 52, 42, 56), fill=color)   # base
    return img


class Bandeja:
    """Ícono con un toggle de escucha y una opción de salir."""

    def __init__(self, nombre: str, on_toggle: Callable[[bool], None],
                 on_salir: Callable[[], None]) -> None:
        self._nombre = nombre
        self._on_toggle = on_toggle
        self._on_salir = on_salir
        self._escuchando = True
        self._icon = None

    def iniciar(self) -> None:
        import pystray

        def toggle(icon, item):
            self._escuchando = not self._escuchando
            self._on_toggle(self._escuchando)
            icon.icon = _icono((80, 200, 120) if self._escuchando else (120, 120, 120))
            icon.title = self._titulo()

        def salir(icon, item):
            icon.stop()
            self._on_salir()

        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: "Pausar escucha" if self._escuchando else "Reanudar escucha",
                toggle,
            ),
            pystray.MenuItem("Salir", salir),
        )
        self._icon = pystray.Icon(
            self._nombre, _icono((80, 200, 120)), self._titulo(), menu
        )
        self._icon.run_detached()      # no bloquea el hilo principal

    def detener(self) -> None:
        if self._icon is not None:
            self._icon.stop()

    def _titulo(self) -> str:
        estado = "escuchando" if self._escuchando else "en pausa"
        return f"{self._nombre} — {estado}"
