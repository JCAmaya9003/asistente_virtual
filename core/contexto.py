"""Contexto conversacional: los últimos N turnos y flags de confianza.
Es la diferencia entre un asistente y un simple ejecutor de comandos.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class Turno:
    texto_usuario: str
    respuesta: str


@dataclass
class Contexto:
    turnos: "deque[Turno]" = field(default_factory=lambda: deque(maxlen=5))
    leyo_contenido_no_confiable: bool = False     # True cuando se lee contenido externo (v5)
    ultima_skill: str | None = None

    def agregar(self, texto_usuario: str, respuesta: str) -> None:
        self.turnos.append(Turno(texto_usuario, respuesta))
