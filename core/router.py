"""Traduce texto libre a una Intencion estructurada. NUNCA produce comandos.

v1: matcher de frases (rápido, determinista, cero alucinación).
v5: se añade el fallback al LLM (Ollama, qwen3:8b, tool calling). El hueco está marcado.

Criterio de coincidencia (endurecido tras el falso positivo "hola" -> skill "hora"):
  1. La frase debe aparecer al INICIO del texto, no en cualquier parte.
  2. La similitud aproximada exige un umbral alto y se compara solo contra el prefijo
     del texto del largo de la frase, no contra la frase entera.
  3. Se prefiere la coincidencia más específica (frase más larga) ante empates.
Fallar cerrado es correcto: un "no entendí" es mucho mejor que ejecutar la skill errónea.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from core.registry import Registry

UMBRAL_POR_DEFECTO = 0.85


@dataclass
class Intencion:
    skill: str
    params: dict = field(default_factory=dict)
    origen: str = "keywords"                      # "keywords" | "llm"
    confianza: float = 0.0


class Router:
    def __init__(self, registry: Registry, umbral: float = UMBRAL_POR_DEFECTO) -> None:
        self._registry = registry
        self._umbral = umbral

    def enrutar(self, texto: str) -> Intencion | None:
        texto_norm = texto.strip().lower()
        if not texto_norm:
            return None

        mejor_skill = None
        mejor_score = 0.0
        mejor_largo = 0

        for skill in self._registry.todas():
            for frase in skill.frases:
                frase_norm = frase.lower()
                score = self._puntuar(texto_norm, frase_norm)
                if score < self._umbral:
                    continue
                # Ante empate de score, gana la frase más específica (la más larga).
                if (score, len(frase_norm)) > (mejor_score, mejor_largo):
                    mejor_skill = skill
                    mejor_score = score
                    mejor_largo = len(frase_norm)

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
        """La frase debe estar al INICIO del texto (exacta o casi).

        Comparar contra el prefijo del largo de la frase evita que un texto corto
        parecido ("hola" vs "hora") gane por accidente, y permite que un texto largo
        que empieza bien ("abre spotify") coincida con su disparador ("abre").
        """
        if texto.startswith(frase):
            return 1.0
        prefijo = texto[:len(frase)]
        return SequenceMatcher(None, prefijo, frase).ratio()
