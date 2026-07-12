"""Skill: decir qué sabe hacer el asistente.

La lista NO está escrita a mano: se genera desde el registry. Cuando agregás una skill
nueva, aparece sola. Una lista hardcodeada se desactualiza a la semana.

Diseño de la respuesta: escuchar diez skills por voz es insoportable, así que habla un
resumen corto e imprime el detalle completo en consola.
"""
from __future__ import annotations

from core.contexto import Contexto
from core.skill import Permisos, Resultado, Skill

# Skills que existen pero no se anuncian (evita el eco de "puedo decirte la ayuda").
OCULTAS = {"ayuda"}


class SkillAyuda(Skill):
    nombre = "ayuda"
    descripcion = "List what the assistant can do."      # EN INGLÉS
    esquema = {"type": "object", "properties": {}, "required": []}
    frases = ("qué podés hacer", "que podes hacer", "qué puedes hacer",
              "que puedes hacer", "qué sabés hacer", "ayuda", "comandos",
              "opciones", "menú", "menu")
    permisos = Permisos()

    # El registry lo inyecta al construir la skill (ver core/registry.py).
    registry = None

    def ejecutar(self, params: dict, ctx: Contexto) -> Resultado:
        skills = [s for s in (self.registry.todas() if self.registry else [])
                  if s.nombre not in OCULTAS]
        skills.sort(key=lambda s: s.nombre)

        if not skills:
            return Resultado(ok=False, mensaje="No tengo ninguna habilidad cargada.")

        # Detalle completo en consola: acá sí conviene ser exhaustivo.
        print("\n  Esto es lo que sé hacer:")
        for s in skills:
            ejemplo = s.frases[0] if s.frases else s.nombre
            estado = "" if self._implementada(s) else "   (todavía no implementada)"
            print(f"    · {s.nombre:12} → «{ejemplo}»{estado}")
        print()

        # Resumen hablado: corto a propósito.
        listos = [s.nombre for s in skills if self._implementada(s)]
        mensaje = f"Sé hacer {len(listos)} cosas: {self._enumerar(listos)}."
        pendientes = [s.nombre for s in skills if not self._implementada(s)]
        if pendientes:
            mensaje += f" Y todavía me falta {self._enumerar(pendientes)}."
        mensaje += " Te dejé el detalle en la consola."

        return Resultado(ok=True, mensaje=mensaje,
                         datos={"skills": [s.nombre for s in skills]})

    @staticmethod
    def _implementada(skill: Skill) -> bool:
        """Una skill placeholder levanta NotImplementedError. Se detecta sin ejecutarla."""
        import inspect
        try:
            fuente = inspect.getsource(skill.ejecutar)
        except (OSError, TypeError):
            return True
        return "raise NotImplementedError" not in fuente

    @staticmethod
    def _enumerar(nombres: list[str]) -> str:
        """'a, b y c' — para que suene natural al hablarlo."""
        legibles = [n.replace("_", " ") for n in nombres]
        if len(legibles) <= 1:
            return "".join(legibles)
        return f"{', '.join(legibles[:-1])} y {legibles[-1]}"
