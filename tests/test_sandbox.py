"""La jaula de rutas debe rechazar todo intento de salir de las raíces permitidas.
En v0.5 se amplía con UNC, symlinks, mayúsculas y ADS de Windows.
"""
from __future__ import annotations

import os

import pytest

from core.sandbox import FueraDeJaula, ruta_segura


def test_rechaza_sin_raices() -> None:
    with pytest.raises(FueraDeJaula):
        ruta_segura("cualquier.txt", ())


def test_acepta_dentro_de_la_raiz(tmp_path) -> None:
    archivo = tmp_path / "ok.txt"
    archivo.write_text("hola")
    resuelta = ruta_segura(str(archivo), (str(tmp_path),))
    assert os.path.exists(resuelta)


def test_rechaza_escape_con_dotdot(tmp_path) -> None:
    fuera = tmp_path / ".." / "fuera.txt"
    with pytest.raises(FueraDeJaula):
        ruta_segura(str(fuera), (str(tmp_path / "subdir"),))

# TODO(v0.5): casos UNC (\\servidor\...), symlinks, mayúsculas y ADS (archivo:stream).
