"""Salida por consola."""
from __future__ import annotations


class SalidaConsola:
    def decir(self, texto: str) -> None:
        print(f"asistente> {texto}")
