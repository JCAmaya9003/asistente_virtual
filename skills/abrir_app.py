r"""Skill: abrir una aplicación por nombre, desde el whitelist de config/apps.yaml.

NO busca ejecutables mágicamente: solo abre lo que el usuario aprobó en apps.yaml.

Cada app declara varios ALIAS ("google", "chrome", "navegador" → la misma app) y un
destino, que puede ser:
  - una ruta a un .exe            → C:\...\chrome.exe
  - un protocolo/URI              → whatsapp://    (apps de la Microsoft Store)
  - una carpeta del shell         → shell:AppsFolder\...

os.startfile() maneja los tres casos igual, que es justo por qué se usa.
"""
from __future__ import annotations

import os
import shlex
import subprocess

from core.config import cargar_apps
from core.contexto import Contexto
from core.skill import Permisos, Resultado, Skill


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos: 'Café' y 'cafe' deben coincidir.

    Whisper devuelve acentos y mayúsculas; el usuario escribe de cualquier forma.
    """
    tabla = str.maketrans("áéíóúüñ", "aeiouun")
    return texto.strip().lower().translate(tabla)


def indice_de_alias(apps: dict) -> dict[str, str]:
    """Aplana apps.yaml a  {alias_normalizado: destino}.

    Acepta dos formatos, para no romper configuraciones viejas:
      chrome: C:\\ruta\\chrome.exe                      (simple)
      chrome: {alias: [google, navegador], destino: C:\\ruta\\chrome.exe}   (con alias)
    """
    indice: dict[str, str] = {}
    for clave, valor in (apps or {}).items():
        if isinstance(valor, dict):
            destino = valor.get("destino")
            alias = list(valor.get("alias") or [])
        else:
            destino = valor
            alias = []
        if not destino:
            continue
        for nombre in [clave, *alias]:
            indice[normalizar(str(nombre))] = str(destino)
    return indice


def resolver(pedido: str, indice: dict[str, str]) -> str | None:
    """Busca el destino. Exacto primero; si no, por prefijo (tolera 'chrome' en
    'chrome por favor' o basura que agregue el STT)."""
    pedido = normalizar(pedido)
    if not pedido:
        return None
    if pedido in indice:
        return indice[pedido]
    # El alias más largo que aparezca al inicio del pedido gana (más específico).
    candidatos = [a for a in indice if pedido.startswith(a)]
    if candidatos:
        return indice[max(candidatos, key=len)]
    return None


class SkillAbrirApp(Skill):
    nombre = "abrir_app"
    descripcion = "Open a desktop application by its known name."     # EN INGLÉS
    esquema = {
        "type": "object",
        "properties": {
            "nombre": {"type": "string", "description": "app name, e.g. 'chrome'"}
        },
        "required": ["nombre"],
    }
    frases = ("abre chrome", "abre la app", "abrime", "abre", "inicia", "abrir")
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
        pedido = (params.get("nombre") or "").strip()
        if not pedido:
            return Resultado(ok=False, mensaje="¿Qué aplicación querés abrir?")

        destino = resolver(pedido, indice_de_alias(cargar_apps()))
        if destino is None:
            return Resultado(
                ok=False,
                mensaje=f"No conozco la app '{pedido}'. Agregala a config/apps.yaml.",
            )
        try:
            self._lanzar(destino)
        except AttributeError:
            return Resultado(ok=False, mensaje="Abrir apps solo funciona en Windows por ahora.")
        except OSError as e:
            return Resultado(ok=False, mensaje=f"No pude abrir '{pedido}': {e}")
        return Resultado(ok=True, mensaje=f"Abriendo {pedido}.")

    @staticmethod
    def _lanzar(destino: str) -> None:
        """os.startfile NO acepta argumentos, y Discord los necesita
        (Update.exe --processStart Discord.exe). Cuando el destino trae argumentos se
        usa subprocess; si no, startfile, que además resuelve URIs y shell:.

        El destino SIEMPRE sale del whitelist de apps.yaml, nunca del usuario: no hay
        superficie de inyección de comandos. Por eso shell=False.
        """
        partes = shlex.split(destino, posix=False)
        if len(partes) > 1:
            subprocess.Popen(partes, shell=False)
        else:
            os.startfile(destino)
