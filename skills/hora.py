"""Skill de referencia: decir la hora. Trivial, sin permisos. FUNCIONAL en v0."""
from __future__ import annotations

from datetime import datetime

from core.contexto import Contexto
from core.skill import Permisos, Resultado, Skill


class SkillHora(Skill):
    nombre = "hora"
    descripcion = "Tell the user the current local time."       # EN INGLÉS para el LLM
    esquema = {"type": "object", "properties": {}, "required": []}
    frases = ("qué hora es", "dime la hora", "la hora", "hora")
    permisos = Permisos()                                       # ninguno

    def ejecutar(self, params: dict, ctx: Contexto) -> Resultado:
        ahora = datetime.now().strftime("%H:%M")
        return Resultado(ok=True, mensaje=f"Son las {ahora}.")
