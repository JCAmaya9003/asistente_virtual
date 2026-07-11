"""Punto de entrada. v1: REPL de texto + voz de salida (Piper).

Flujo:  texto → Router → Compuerta → Skill → Persona → Salida (voz + consola)

Si no hay voz configurada (falta el modelo o piper), cae a salida de texto sin romperse.
Ejecutar desde la raíz del repo, con el venv activo:  python main.py
"""
from __future__ import annotations

from pathlib import Path

from adapters.input_cli import EntradaCLI
from adapters.output_console import SalidaConsola
from adapters.output_tts import SalidaTTS
from core.audit import Auditor
from core.config import cargar_persona
from core.contexto import Contexto
from core.gate import Compuerta
from core.persona import Persona
from core.registry import cargar_skills
from core.router import Router


def confirmar_por_consola(pregunta: str) -> bool:
    return input(f"{pregunta} [s/N] ").strip().lower() in ("s", "si", "sí")


def construir_salida(persona_cfg: dict):
    """Salida con voz si hay modelo Piper disponible; si no, salida de texto."""
    voz = persona_cfg.get("voz") or {}
    modelo = voz.get("modelo")
    if modelo and Path(modelo).exists():
        try:
            from adapters.tts_piper import PiperEngine
            engine = PiperEngine(
                modelo,
                use_cuda=bool(voz.get("use_cuda", False)),
                length_scale=float(voz.get("length_scale", 1.0)),
            )
            print("[voz activa: Piper]")
            return SalidaTTS(engine)
        except Exception as e:
            print(f"[voz desactivada: {e}] Uso salida de texto.")
    else:
        print("[voz desactivada: configurá 'voz.modelo' en config/persona.yaml] Uso salida de texto.")
    return SalidaConsola()


def main() -> None:
    persona_cfg = cargar_persona()
    registry = cargar_skills()
    router = Router(registry)
    auditor = Auditor()
    compuerta = Compuerta(registry, auditor, confirmar=confirmar_por_consola)
    persona = Persona(persona_cfg)
    contexto = Contexto()
    entrada = EntradaCLI()
    salida = construir_salida(persona_cfg)

    print(f"Listo. {len(registry)} skills cargadas. Escribí 'salir' para terminar.")
    while True:
        texto = entrada.leer()
        if texto is None or texto.strip().lower() in ("salir", "exit", "quit"):
            salida.decir("Hasta luego.")
            break

        intencion = router.enrutar(texto)
        if intencion is None:
            bruto = "No entendí. ¿Podés reformularlo?"
        else:
            resultado = compuerta.ejecutar(intencion, contexto)
            bruto = resultado.mensaje

        respuesta = persona.estilizar(bruto)
        salida.decir(respuesta)
        contexto.agregar(texto, respuesta)


if __name__ == "__main__":
    main()