"""Punto de entrada. v0: REPL de texto. Sin micrófono, sin voz.

Flujo:  texto → Router → Compuerta → Skill → Persona → Salida

Ejecutar desde la raíz del repo:  python main.py
"""
from __future__ import annotations

from adapters.input_cli import EntradaCLI
from adapters.output_console import SalidaConsola
from core.audit import Auditor
from core.contexto import Contexto
from core.gate import Compuerta
from core.persona import Persona
from core.registry import cargar_skills
from core.router import Router


def confirmar_por_consola(pregunta: str) -> bool:
    return input(f"{pregunta} [s/N] ").strip().lower() in ("s", "si", "sí")


def main() -> None:
    registry = cargar_skills()
    router = Router(registry)
    auditor = Auditor()
    compuerta = Compuerta(registry, auditor, confirmar=confirmar_por_consola)
    persona = Persona()
    contexto = Contexto()
    entrada = EntradaCLI()
    salida = SalidaConsola()

    salida.decir(f"Listo. {len(registry)} skills cargadas. Escribí 'salir' para terminar.")
    while True:
        texto = entrada.leer()
        if texto is None or texto.strip().lower() in ("salir", "exit", "quit"):
            salida.decir("Hasta luego.")
            break

        intencion = router.enrutar(texto)
        if intencion is None:
            respuesta = "No entendí. ¿Podés reformularlo?"
        else:
            resultado = compuerta.ejecutar(intencion, contexto)
            respuesta = persona.estilizar(resultado.mensaje)

        salida.decir(respuesta)
        contexto.agregar(texto, respuesta)


if __name__ == "__main__":
    main()
