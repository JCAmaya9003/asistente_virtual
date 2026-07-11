"""Contrato base de una Skill y los tipos que la rodean.

Una Skill es una unidad de acción autocontenida. La regla de diseño es:
agregar una skill nueva cuesta ~15 líneas y no toca nada de core/.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:  # evita import circular; solo se necesita para type hints
    from core.contexto import Contexto


@dataclass(frozen=True)
class Permisos:
    """Manifiesto declarativo. El núcleo NIEGA por defecto lo que no esté declarado."""
    lee_archivos: bool = False
    escribe_archivos: bool = False
    red: bool = False
    destructiva: bool = False
    raices_permitidas: tuple[str, ...] = ()


@dataclass
class Resultado:
    """Lo que devuelve una skill tras ejecutarse."""
    ok: bool
    mensaje: str                                  # texto para hablarle al usuario
    datos: dict[str, Any] = field(default_factory=dict)


class Skill(ABC):
    """Clase base. Cada skill concreta define los atributos de clase e implementa ejecutar()."""

    nombre: str = ""                              # identificador único, p.ej. "abrir_app"
    descripcion: str = ""                         # EN INGLÉS: tool description del LLM (v5)
    esquema: dict[str, Any] = {}                  # JSON Schema de los parámetros
    frases: tuple[str, ...] = ()                  # patrones para el matcher rápido (v0)
    permisos: Permisos = Permisos()

    @abstractmethod
    def ejecutar(self, params: dict[str, Any], ctx: "Contexto") -> Resultado:
        """Ejecuta la acción. NO validar permisos aquí: de eso se encarga la compuerta."""
        raise NotImplementedError

    def extraer_params(self, texto: str) -> dict[str, Any]:
        """Extracción ligera de parámetros en la era pre-LLM (v0–v4).

        Por defecto no extrae nada. Una skill que necesita params la sobreescribe.
        En v5 el LLM provee los params directamente y este método se ignora.
        """
        return {}
