"""Jaula de rutas. Una skill que toca archivos recibe raíces permitidas y solo puede
operar DENTRO de ellas.

Defiende contra: falta de raíces, rutas de red (UNC), alternate data streams de Windows,
y escapes por '..' o symlinks (os.path.realpath resuelve ambos antes de comparar).
La comparación usa commonpath + normcase para no fallar por prefijos parciales ni por
mayúsculas/minúsculas (Windows es insensible a mayúsculas).
"""
from __future__ import annotations

import os


class FueraDeJaula(Exception):
    pass


def _componente_final(candidata: str) -> str:
    """Último componente de la ruta, considerando separadores de Windows y POSIX."""
    normal = candidata.replace("\\", "/")
    return normal.rsplit("/", 1)[-1]


def _motivo_peligro(candidata: str) -> str | None:
    """Rechazos que NO dependen del sistema de archivos (se validan como texto).

    Fallan cerrado a propósito: ante la duda, se rechaza.
    """
    normal = candidata.replace("\\", "/")
    if normal.startswith("//"):                     # UNC: \\servidor\recurso
        return "ruta de red (UNC) no permitida"
    if ":" in _componente_final(candidata):         # ADS de Windows: archivo.txt:stream
        return "alternate data stream no permitido"
    return None


def ruta_segura(candidata: str, raices_permitidas: tuple[str, ...]) -> str:
    """Devuelve la ruta absoluta REAL si cae dentro de alguna raíz permitida; si no, lanza."""
    if not raices_permitidas:
        raise FueraDeJaula("la skill no declaró raíces permitidas")

    motivo = _motivo_peligro(candidata)
    if motivo:
        raise FueraDeJaula(motivo)

    real = os.path.normcase(os.path.realpath(candidata))
    for raiz in raices_permitidas:
        raiz_real = os.path.normcase(os.path.realpath(raiz))
        try:
            # commonpath evita el bug clásico de startswith con prefijos parciales
            # (p.ej. /datos vs /datos-secretos)
            if os.path.commonpath([real, raiz_real]) == raiz_real:
                return real
        except ValueError:
            continue  # unidades distintas (Windows): no puede estar dentro
    raise FueraDeJaula(f"ruta fuera de la jaula: {candidata}")
