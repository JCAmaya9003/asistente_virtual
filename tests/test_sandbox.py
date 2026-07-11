"""La jaula de rutas debe rechazar TODO intento de salir de las raíces permitidas.
Cubre los vectores de Windows: '..', UNC, ADS, symlinks y prefijos parciales.
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


def test_rechaza_ruta_unc() -> None:
    with pytest.raises(FueraDeJaula):
        ruta_segura(r"\\servidor\recurso\secreto.txt", ("/cualquier/raiz",))


def test_rechaza_alternate_data_stream(tmp_path) -> None:
    with pytest.raises(FueraDeJaula):
        ruta_segura(str(tmp_path / "nota.txt:oculto"), (str(tmp_path),))


def test_rechaza_prefijo_parcial(tmp_path) -> None:
    # /datos NO debe permitir escribir en /datos-secretos
    raiz = tmp_path / "datos"
    raiz.mkdir()
    hermano = tmp_path / "datos-secretos"
    hermano.mkdir()
    objetivo = hermano / "f.txt"
    objetivo.write_text("x")
    with pytest.raises(FueraDeJaula):
        ruta_segura(str(objetivo), (str(raiz),))


def test_rechaza_symlink_que_escapa(tmp_path) -> None:
    raiz = tmp_path / "jaula"
    raiz.mkdir()
    afuera = tmp_path / "secreto.txt"
    afuera.write_text("x")
    enlace = raiz / "enlace.txt"
    try:
        enlace.symlink_to(afuera)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks no soportados en este entorno")
    # realpath resuelve el symlink a 'afuera', que está fuera de la jaula
    with pytest.raises(FueraDeJaula):
        ruta_segura(str(enlace), (str(raiz),))
