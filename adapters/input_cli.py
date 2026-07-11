"""Entrada por teclado (REPL). Contraparte natural de SalidaConsola para desarrollo sin voz."""
from __future__ import annotations


class EntradaCLI:
    def leer(self) -> str | None:
        try:
            return input("tú> ")
        except (EOFError, KeyboardInterrupt):
            return None
