"""Carga de configuración YAML del proyecto (config/*.yaml)."""
from __future__ import annotations

from pathlib import Path

import yaml

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _cargar_yaml(nombre: str) -> dict:
    ruta = _CONFIG_DIR / nombre
    if not ruta.exists():
        return {}
    with ruta.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def raices_de(skill: str) -> list[str]:
    """Raíces permitidas para una skill, leídas de config/permisos.yaml.
    Devuelve [] si la skill no tiene carpetas configuradas.
    """
    permisos = _cargar_yaml("permisos.yaml")
    valor = permisos.get(skill, [])
    return list(valor) if isinstance(valor, list) else []
