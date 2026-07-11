"""Skill: reportar el clima de hoy. PLACEHOLDER.

Requiere red, así que su implementación llega más adelante. Ya declara red=True para
respetar el modelo de permisos: el núcleo la tratará como skill de red desde ahora.
"""
from __future__ import annotations

from core.contexto import Contexto
from core.skill import Permisos, Resultado, Skill


class SkillClima(Skill):
    nombre = "clima"
    descripcion = "Report today's weather for the user's location."   # EN INGLÉS
    esquema = {
        "type": "object",
        "properties": {"ciudad": {"type": "string"}},
        "required": [],
    }
    frases = ("qué clima hace", "cómo está el clima", "el clima", "clima", "tiempo")
    permisos = Permisos(red=True)                    # el núcleo respeta esta declaración

    def ejecutar(self, params: dict, ctx: Contexto) -> Resultado:
        # TODO: consultar la API del clima (respetando la regla de contenido no confiable).
        raise NotImplementedError
