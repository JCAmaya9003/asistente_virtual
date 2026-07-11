"""Jaula de rutas. Una skill que toca archivos recibe raíces permitidas y solo puede
operar dentro de ellas.

La base ya rechaza lo evidente (rutas fuera de la raíz, escapes con '..').
v0.5 la endurece con la matriz de Windows: UNC, symlinks, mayúsculas y ADS.
Ver tests/test_sandbox.py.
"""
from __future__ import annotations

import os


class FueraDeJaula(Exception):
    pass


def ruta_segura(candidata: str, raices_permitidas: tuple[str, ...]) -> str:
    """Devuelve la ruta absoluta REAL si cae dentro de alguna raíz; si no, lanza."""
    if not raices_permitidas:
        raise FueraDeJaula("la skill no declaró raíces permitidas")

    real = os.path.normcase(os.path.realpath(candidata))
    for raiz in raices_permitidas:
        raiz_real = os.path.normcase(os.path.realpath(raiz))
        try:
            # commonpath evita el bug clásico de startswith con prefijos parciales
            if os.path.commonpath([real, raiz_real]) == raiz_real:
                return real
        except ValueError:
            continue  # rutas en unidades distintas (Windows)
    raise FueraDeJaula(f"ruta fuera de la jaula: {candidata}")
    # TODO(v0.5): endurecer para UNC (\\servidor\...), symlinks y ADS (archivo:stream).
