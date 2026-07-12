"""Skill: tomar una nota. Primera skill que ESCRIBE en disco.

Diseño seguro: el usuario NO controla la ruta. La nota siempre va a un archivo fijo
(notas.txt) dentro de una carpeta declarada en config/permisos.yaml. Aun así el destino
pasa por la jaula como defensa en profundidad. Declara escribe_archivos=True.
"""
from __future__ import annotations

from pathlib import Path

from core.config import raices_de
from core.contexto import Contexto
from core.sandbox import FueraDeJaula, ruta_segura
from core.skill import Permisos, Resultado, Skill

_ARCHIVO = "notas.txt"


class SkillNota(Skill):
    nombre = "nota"
    descripcion = "Append a short note to the user's notes file."     # EN INGLÉS
    esquema = {
        "type": "object",
        "properties": {"texto": {"type": "string", "description": "the note content"}},
        "required": ["texto"],
    }
    frases = ("tomá nota comprar pan", "tomá nota", "toma nota", "anotá", "anota", "nota")
    permisos = Permisos(escribe_archivos=True)

    _DISPARADORES = ("tomá nota", "toma nota", "anotá", "anota", "nota")

    def extraer_params(self, texto: str) -> dict:
        t = texto.strip()
        bajo = t.lower()
        for disparador in self._DISPARADORES:
            if bajo.startswith(disparador):
                return {"texto": t[len(disparador):].strip(" :,-")}
        return {"texto": ""}

    def ejecutar(self, params: dict, ctx: Contexto) -> Resultado:
        texto = (params.get("texto") or "").strip()
        if not texto:
            return Resultado(ok=False, mensaje="¿Qué querés que anote?")

        raices = raices_de(self.nombre)
        if not raices:
            return Resultado(
                ok=False,
                mensaje="No hay carpeta configurada para notas. Agregala en config/permisos.yaml.",
            )

        destino = Path(raices[0]) / _ARCHIVO
        try:
            ruta = ruta_segura(str(destino), tuple(raices))
        except FueraDeJaula as e:
            return Resultado(ok=False, mensaje=f"Ruta no permitida: {e}")

        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
        return Resultado(ok=True, mensaje="Anotado.")
