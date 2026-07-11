"""Compuerta de ejecución. TODA intención pasa por aquí. Nada la esquiva.

Intención → Validación → Confirmación (si destructiva) → Ejecución (en jaula, con log)
                 │
                 └→ Rechazo (queda en el log)
"""
from __future__ import annotations

from typing import Callable

from core.audit import Auditor
from core.contexto import Contexto
from core.registry import Registry
from core.router import Intencion
from core.skill import Resultado


class Compuerta:
    def __init__(self, registry: Registry, auditor: Auditor,
                 confirmar: Callable[[str], bool] | None = None) -> None:
        self._registry = registry
        self._auditor = auditor
        # función que pide confirmación al usuario; None = auto-negar destructivas
        self._confirmar = confirmar

    def ejecutar(self, intencion: Intencion, ctx: Contexto) -> Resultado:
        skill = self._registry.obtener(intencion.skill)

        # 1. Validación -------------------------------------------------------
        if skill is None:
            return self._rechazar(intencion, "skill inexistente")

        # Regla de contenido no confiable → modo solo-lectura (rompe la trifecta letal).
        # Ya cableada aunque nada la active todavía en v0.
        if ctx.leyo_contenido_no_confiable and (
            skill.permisos.red or skill.permisos.escribe_archivos
        ):
            return self._rechazar(intencion, "modo solo-lectura: se leyó contenido no confiable")

        # TODO(v0.5): validar intencion.params contra skill.esquema (JSON Schema).

        # 2. Confirmación (solo destructivas) ---------------------------------
        if skill.permisos.destructiva:
            pregunta = f"¿Confirmás la acción destructiva '{skill.nombre}'?"
            if self._confirmar is None or not self._confirmar(pregunta):
                return self._rechazar(intencion, "confirmación denegada")

        # 3. Ejecución --------------------------------------------------------
        try:
            resultado = skill.ejecutar(intencion.params, ctx)
        except NotImplementedError:
            return self._rechazar(intencion, "skill no implementada todavía")
        except Exception as e:  # la compuerta nunca debe tumbar el proceso
            return self._rechazar(intencion, f"error en ejecución: {e}")

        self._auditor.registrar(
            skill=skill.nombre, params=intencion.params, origen=intencion.origen,
            resultado="ok" if resultado.ok else "fallo",
        )
        ctx.ultima_skill = skill.nombre
        return resultado

    def _rechazar(self, intencion: Intencion, motivo: str) -> Resultado:
        self._auditor.registrar(
            skill=intencion.skill, params=intencion.params, origen=intencion.origen,
            resultado="rechazo", motivo=motivo,
        )
        return Resultado(ok=False, mensaje=f"No pude hacerlo: {motivo}")
