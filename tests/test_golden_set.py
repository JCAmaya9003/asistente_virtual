"""Golden set: frases → skill esperada. Es el criterio de aceptación del router.
Crece hasta 50–100 casos antes de la v5.

Los casos NEGATIVOS son tan importantes como los positivos: el router debe fallar
cerrado. Ejecutar la skill equivocada es peor que decir "no entendí".
"""
from __future__ import annotations

import pytest

from core.registry import cargar_skills
from core.router import Router

POSITIVOS = [
    ("qué hora es", "hora"),
    ("dime la hora", "hora"),
    ("hora", "hora"),
    ("abre spotify", "abrir_app"),
    ("abrime chrome", "abrir_app"),
    ("inicia discord", "abrir_app"),
    ("cómo está el clima", "clima"),
    ("qué clima hace", "clima"),
    ("tomá nota comprar pan", "nota"),
    ("anota llamar al dentista", "nota"),
]

# Texto que NO debe disparar ninguna skill. Varios son trampas fonéticas reales
# del español ("hola"/"hora", "ahora"/"hora") o errores típicos de transcripción.
NEGATIVOS = [
    "hola",
    "hgolaaaa",
    "obvio",
    "ahora",
    "ahorita",
    "cómo estás",
    "gracias",
    "hazme un sándwich de milanesa",
]


@pytest.fixture(scope="module")
def router() -> Router:
    return Router(cargar_skills())


@pytest.mark.parametrize("texto,skill_esperada", POSITIVOS)
def test_enruta_a_la_skill_correcta(router: Router, texto: str, skill_esperada: str) -> None:
    intencion = router.enrutar(texto)
    assert intencion is not None, f"no enrutó: {texto!r}"
    assert intencion.skill == skill_esperada


@pytest.mark.parametrize("texto", NEGATIVOS)
def test_no_enruta_texto_desconocido(router: Router, texto: str) -> None:
    intencion = router.enrutar(texto)
    assert intencion is None, (
        f"falso positivo: {texto!r} disparó la skill "
        f"{intencion.skill!r} con confianza {intencion.confianza:.2f}"
    )


def test_extrae_nombre_de_app(router: Router) -> None:
    intencion = router.enrutar("abre spotify")
    assert intencion is not None
    assert intencion.params.get("nombre") == "spotify"


def test_extrae_texto_de_nota(router: Router) -> None:
    intencion = router.enrutar("tomá nota comprar pan")
    assert intencion is not None
    assert intencion.params.get("texto") == "comprar pan"
