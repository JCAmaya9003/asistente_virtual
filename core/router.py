"""Traduce texto libre a una Intencion estructurada. NUNCA produce comandos.

v0: solo el matcher de frases (rápido, determinista, cero alucinación).
v5: se añade el fallback al LLM (Ollama, qwen3:8b, tool calling). El hueco está marcado.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from core.registry import Registry


@dataclass
class Intencion:
    skill: str
    params: dict = field(default_factory=dict)
    origen: str = "keywords"                      # "keywords" | "llm"
    confianza: float = 0.0


class Router:
    def __init__(self, registry: Registry, umbral: float = 0.6) -> None:
        self._registry = registry
        self._umbral = umbral

    def enrutar(self, texto: str) -> Intencion | None:
        texto_norm = texto.strip().lower()
        if not texto_norm:
            return None

        mejor_skill = None
        mejor_score = 0.0
        for skill in self._registry.todas():
            for frase in skill.frases:
                score = self._puntuar(texto_norm, frase.lower())
                if score >= self._umbral and score > mejor_score:
                    mejor_skill, mejor_score = skill, score

        if mejor_skill is not None:
            return Intencion(
                skill=mejor_skill.nombre,
                params=mejor_skill.extraer_params(texto),
                origen="keywords",
                confianza=mejor_score,
            )

        # --- v5: aquí entra el fallback al LLM ---
        # return self._enrutar_con_llm(texto)
        return None

    @staticmethod
    def _puntuar(texto: str, frase: str) -> float:
        """Substring exacto = 1.0; si no, similitud aproximada (tolera errores de STT)."""
        if frase in texto:
            return 1.0
        return SequenceMatcher(None, texto, frase).ratio()
