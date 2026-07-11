"""Capa de persona. Reescribe la respuesta según un perfil de estilo ANTES del TTS.
Es donde vive el carácter del asistente, 100% independiente del motor de voz.

v0: passthrough (devuelve el texto tal cual).
v1: aplica config/persona.yaml (vocabulario, muletillas, ritmo, longitud).
"""
from __future__ import annotations


class Persona:
    def __init__(self, perfil: dict | None = None) -> None:
        self._perfil = perfil or {}

    def estilizar(self, texto: str) -> str:
        # v1: aplicar el perfil de estilo aquí.
        return texto
