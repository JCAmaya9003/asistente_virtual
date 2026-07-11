"""Descubre y registra skills. El router y la compuerta consultan el registry;
nadie más conoce las skills concretas.

cargar_skills() importa cada módulo de skills/ y registra automáticamente toda
subclase de Skill que encuentre. Por eso agregar una skill NO requiere tocar core/.
"""
from __future__ import annotations

import importlib
import pkgutil

from core.skill import Skill


class Registry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def registrar(self, skill: Skill) -> None:
        if not skill.nombre:
            raise ValueError(f"skill sin nombre: {type(skill).__name__}")
        if skill.nombre in self._skills:
            raise ValueError(f"skill duplicada: {skill.nombre}")
        self._skills[skill.nombre] = skill

    def obtener(self, nombre: str) -> Skill | None:
        return self._skills.get(nombre)

    def todas(self) -> list[Skill]:
        return list(self._skills.values())

    def __len__(self) -> int:
        return len(self._skills)


def cargar_skills(paquete: str = "skills") -> Registry:
    """Importa cada módulo de skills/ y registra toda subclase de Skill encontrada."""
    registry = Registry()
    modulo = importlib.import_module(paquete)
    for _, nombre_mod, _ in pkgutil.iter_modules(modulo.__path__):
        mod = importlib.import_module(f"{paquete}.{nombre_mod}")
        for attr in vars(mod).values():
            if isinstance(attr, type) and issubclass(attr, Skill) and attr is not Skill:
                registry.registrar(attr())
    return registry
