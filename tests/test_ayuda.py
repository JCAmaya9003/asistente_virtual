"""La ayuda se autogenera desde el registry: agregar una skill la actualiza sola."""
from __future__ import annotations

from core.contexto import Contexto
from core.registry import cargar_skills
from core.router import Router
from skills.ayuda import SkillAyuda


def test_lista_todas_las_skills_menos_la_propia() -> None:
    registry = cargar_skills()
    ayuda = registry.obtener("ayuda")
    resultado = ayuda.ejecutar({}, Contexto())

    listadas = resultado.datos["skills"]
    assert resultado.ok
    assert "ayuda" not in listadas, "no debe anunciarse a sí misma"
    for esperada in ("hora", "abrir_app", "nota", "clima"):
        assert esperada in listadas


def test_distingue_las_no_implementadas() -> None:
    """'clima' es un placeholder: la ayuda no debe prometer algo que no hace."""
    registry = cargar_skills()
    resultado = registry.obtener("ayuda").ejecutar({}, Contexto())
    assert "falta" in resultado.mensaje and "clima" in resultado.mensaje
    assert "hora" in resultado.mensaje


def test_se_autogenera_al_agregar_una_skill() -> None:
    """El punto de todo el diseño: una skill nueva aparece sin tocar la ayuda."""
    from core.registry import Registry
    from core.skill import Permisos, Resultado, Skill

    class SkillInventada(Skill):
        nombre = "regar_plantas"
        frases = ("regá las plantas",)
        permisos = Permisos()

        def ejecutar(self, params, ctx):
            return Resultado(ok=True, mensaje="listo")

    registry = Registry()
    ayuda = SkillAyuda()
    ayuda.registry = registry
    registry.registrar(ayuda)
    registry.registrar(SkillInventada())

    resultado = ayuda.ejecutar({}, Contexto())
    assert "regar_plantas" in resultado.datos["skills"]
    assert "regar plantas" in resultado.mensaje      # se lee natural al hablarlo


def test_enrutan_las_frases_de_ayuda() -> None:
    router = Router(cargar_skills())
    for frase in ("ayuda", "qué podés hacer", "comandos", "opciones"):
        intencion = router.enrutar(frase)
        assert intencion is not None, f"no enrutó: {frase!r}"
        assert intencion.skill == "ayuda"
