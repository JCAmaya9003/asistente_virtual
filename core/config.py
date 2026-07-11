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
    """Raíces permitidas para una skill, leídas de config/permisos.yaml."""
    permisos = _cargar_yaml("permisos.yaml")
    valor = permisos.get(skill, [])
    return list(valor) if isinstance(valor, list) else []


def cargar_persona() -> dict:
    """Perfil de estilo y configuración de voz, desde config/persona.yaml."""
    return _cargar_yaml("persona.yaml")


def cargar_audio() -> dict:
    """Configuración de STT y captura, desde config/audio.yaml."""
    return _cargar_yaml("audio.yaml")


def cargar_apps() -> dict:
    """Whitelist de aplicaciones, desde config/apps.yaml."""
    return _cargar_yaml("apps.yaml")


def nombres_de_apps() -> list[str]:
    """Todos los nombres y alias de apps. Se le pasan a Whisper como initial_prompt para
    que transcriba 'Chrome' y no 'crom' (§7.3 del ARCHITECTURE.md).
    """
    nombres: list[str] = []
    for clave, valor in (cargar_apps() or {}).items():
        nombres.append(str(clave))
        if isinstance(valor, dict):
            nombres.extend(str(a) for a in (valor.get("alias") or []))
    return nombres
