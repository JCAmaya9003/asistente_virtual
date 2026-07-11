"""Capa de persona. Reescribe la respuesta según el perfil de estilo ANTES del TTS.
Es donde vive el carácter del asistente, 100% independiente del motor de voz.

v1: normalización para TTS (espacios, puntuación final) + muletillas configurables.
v5: el restyling profundo lo hará el LLM; el gancho está marcado en estilizar().
"""
from __future__ import annotations

import random
import re


class Persona:
    def __init__(self, perfil: dict | None = None) -> None:
        perfil = perfil or {}
        self._tono = perfil.get("tono", "neutral")
        self._muletillas = [m for m in (perfil.get("muletillas") or []) if m]

    def estilizar(self, texto: str) -> str:
        texto = re.sub(r"\s+", " ", texto or "").strip()
        if not texto:
            return ""

        # --- v5: aquí el LLM podrá reescribir el texto con el carácter completo ---

        if self._muletillas and self._tono == "casual":
            texto = f"{random.choice(self._muletillas)}, {texto}"
        if texto[-1] not in ".!?":               # ayuda a la prosodia del TTS
            texto += "."
        return texto