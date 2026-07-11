"""Skill: abrir una aplicación por nombre, desde el whitelist de config/apps.yaml.

NO busca ejecutables mágicamente: solo abre lo que el usuario aprobó en apps.yaml.
El descubrimiento automático de .lnk del menú de inicio (con aprobación) llega en v0.5.
"""
from __future__ import annotations

import os

from core.config import cargar_apps
from core.contexto import Contexto
from core.skill import Permisos, Resultado, Skill


class SkillAbrirApp(Skill):
    nombre = "abrir_app"
    descripcion = "Open a desktop application by its known name."     # EN INGLÉS
    esquema = {
        "type": "object",
        "properties": {
            "nombre": {"type": "string", "description": "app name, e.g. 'spotify'"}
        },
        "required": ["nombre"],
    }
    frases = ("abre la app", "abrime", "abre", "inicia", "abrir")
    # Lanzar un binario del whitelist NO toca la jaula de archivos → sin permisos de FS.
    permisos = Permisos()

    _DISPARADORES = ("abrime la app", "abre la app", "abrime", "abrir", "abre", "inicia")

    def extraer_params(self, texto: str) -> dict:
        t = texto.strip().lower()
        for disparador in self._DISPARADORES:          # más largos primero
            if t.startswith(disparador):
                return {"nombre": t[len(disparador):].strip()}
        return {"nombre": ""}

    def ejecutar(self, params: dict, ctx: Contexto) -> Resultado:
        nombre = (params.get("nombre") or "").strip().lower()
        if not nombre:
            return Resultado(ok=False, mensaje="¿Qué aplicación querés abrir?")

        apps = cargar_apps()
        ruta = apps.get(nombre)
        if ruta is None:
            return Resultado(
                ok=False,
                mensaje=f"No conozco la app '{nombre}'. Agregala a config/apps.yaml.",
            )
        try:
            os.startfile(ruta)                          # Windows
        except AttributeError:
            # os.startfile no existe fuera de Windows. Fallback multiplataforma llega luego.
            return Resultado(ok=False, mensaje="Abrir apps solo funciona en Windows por ahora.")
        except OSError as e:
            return Resultado(ok=False, mensaje=f"No pude abrir '{nombre}': {e}")
        return Resultado(ok=True, mensaje=f"Abriendo {nombre}.")
