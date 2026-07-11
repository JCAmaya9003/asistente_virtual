"""Punto de entrada.

  python main.py          → REPL de texto (escribís, te responde con voz)
  python main.py --voz    → push-to-talk (Enter, hablás, te responde con voz)

Flujo:  entrada → Router → Compuerta → Skill → Persona → Salida

Todo degrada con elegancia: sin modelo Piper responde por consola; sin CUDA transcribe
en CPU; sin micrófono o sin faster-whisper, cae al REPL de texto.
"""
from __future__ import annotations

import sys
from pathlib import Path

from adapters.input_cli import EntradaCLI
from adapters.output_console import SalidaConsola
from adapters.output_tts import SalidaTTS
from core.audit import Auditor
from core.config import cargar_apps, cargar_audio, cargar_persona
from core.contexto import Contexto
from core.gate import Compuerta
from core.persona import Persona
from core.registry import cargar_skills
from core.router import Router

SALIDAS = ("salir", "exit", "quit")


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


def construir_entrada(usar_voz: bool):
    """Micrófono si se pidió --voz y todo está disponible; si no, teclado."""
    if not usar_voz:
        return EntradaCLI()
    try:
        from adapters.input_voice import EntradaVoz
        from adapters.stt_whisper import WhisperEngine, construir_initial_prompt

        cfg = cargar_audio()
        stt = cfg.get("stt") or {}
        cap = cfg.get("captura") or {}

        print("[oído] cargando el modelo, esto tarda la primera vez...")
        engine = WhisperEngine(
            modelo=stt.get("modelo", "large-v3"),
            device=stt.get("device", "auto"),
            compute_type=stt.get("compute_type", "auto"),
            idioma=stt.get("idioma", "es"),
            initial_prompt=construir_initial_prompt(list(cargar_apps().keys())),
        )
        print(f"[oído activo: faster-whisper en {engine.dispositivo}]")
        return EntradaVoz(
            engine,
            sample_rate=int(cap.get("sample_rate", 16000)),
            bloque_ms=int(cap.get("bloque_ms", 100)),
            silencio_ms=int(cap.get("silencio_ms", 1200)),
            umbral_silencio=float(cap.get("umbral_silencio", 0.015)),
            max_segundos=int(cap.get("max_segundos", 15)),
        )
    except Exception as e:
        print(f"[oído desactivado: {e}] Uso el teclado.")
        return EntradaCLI()


def main() -> None:
    usar_voz = "--voz" in sys.argv

    persona_cfg = cargar_persona()
    registry = cargar_skills()
    router = Router(registry)
    auditor = Auditor()
    compuerta = Compuerta(registry, auditor, confirmar=confirmar_por_consola)
    persona = Persona(persona_cfg)
    contexto = Contexto()
    salida = construir_salida(persona_cfg)
    entrada = construir_entrada(usar_voz)

    print(f"Listo. {len(registry)} skills cargadas. Decí o escribí 'salir' para terminar.")
    while True:
        texto = entrada.leer()
        if texto is None or texto.strip().lower() in SALIDAS:
            salida.decir("Hasta luego.")
            break
        if not texto.strip():
            continue

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
