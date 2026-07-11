"""Golden set: frases → (skill, params) esperados. Es el criterio de aceptación del router.
Arranca con unos pocos casos; crece hasta 50–100 antes de la v5.
"""
from __future__ import annotations

import pytest

from core.registry import cargar_skills
from core.router import Router

CASOS = [
    ("qué hora es", "hora"),
    ("dime la hora", "hora"),
    ("abre spotify", "abrir_app"),
    ("abrime chrome", "abrir_app"),
    ("cómo está el clima", "clima"),
    ("tomá nota comprar pan", "nota"),
    ("anota llamar al dentista", "nota"),
]


@pytest.fixture(scope="module")
def router() -> Router:
    return Router(cargar_skills())


@pytest.mark.parametrize("texto,skill_esperada", CASOS)
def test_enruta_a_la_skill_correcta(router: Router, texto: str, skill_esperada: str) -> None:
    intencion = router.enrutar(texto)
    assert intencion is not None, f"no enrutó: {texto!r}"
    assert intencion.skill == skill_esperada


def test_extrae_nombre_de_app(router: Router) -> None:
    intencion = router.enrutar("abre spotify")
    assert intencion is not None
    assert intencion.params.get("nombre") == "spotify"


def test_extrae_texto_de_nota(router: Router) -> None:
    intencion = router.enrutar("tomá nota comprar pan")
    assert intencion is not None
    assert intencion.params.get("texto") == "comprar pan"


def test_texto_desconocido_no_enruta(router: Router) -> None:
    assert router.enrutar("hazme un sándwich de milanesa") is None
