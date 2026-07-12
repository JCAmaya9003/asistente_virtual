"""Punto de entrada.

  python main.py            → REPL de texto (escribís, te responde con voz)
  python main.py --voz      → push-to-talk en la terminal (Enter, hablás)
  python main.py --daemon   → vive en la bandeja; hotkey global para hablar

Flujo (idéntico en los tres modos):
  entrada → Router → Compuerta → Skill → Persona → Salida

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
from core.config import cargar_audio, cargar_persona, nombres_de_apps
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


def construir_stt():
    """Motor de transcripción. Lanza si no está disponible: el que llama decide qué hacer."""
    from adapters.stt_whisper import WhisperEngine, construir_initial_prompt

    stt_cfg = (cargar_audio().get("stt") or {})
    print("[oído] cargando el modelo, esto tarda la primera vez...")
    engine = WhisperEngine(
        modelo=stt_cfg.get("modelo", "large-v3"),
        device=stt_cfg.get("device", "auto"),
        compute_type=stt_cfg.get("compute_type", "auto"),
        idioma=stt_cfg.get("idioma", "es"),
        initial_prompt=construir_initial_prompt(nombres_de_apps()),
    )
    print(f"[oído activo: faster-whisper en {engine.dispositivo}]")
    return engine


def construir_entrada(usar_voz: bool):
    """Micrófono si se pidió --voz y todo está disponible; si no, teclado."""
    if not usar_voz:
        return EntradaCLI()
    try:
        from adapters.input_voice import EntradaVoz

        cap = (cargar_audio().get("captura") or {})
        return EntradaVoz(
            construir_stt(),
            sample_rate=int(cap.get("sample_rate", 16000)),
            bloque_ms=int(cap.get("bloque_ms", 100)),
            silencio_ms=int(cap.get("silencio_ms", 1200)),
            umbral_silencio=float(cap.get("umbral_silencio", 0.015)),
            max_segundos=int(cap.get("max_segundos", 15)),
        )
    except Exception as e:
        print(f"[oído desactivado: {e}] Uso el teclado.")
        return EntradaCLI()


def construir_procesador(router: Router, compuerta: Compuerta, persona: Persona,
                         contexto: Contexto):
    """El corazón compartido por TODOS los modos: texto → respuesta hablada."""
    def procesar(texto: str) -> str:
        intencion = router.enrutar(texto)
        if intencion is None:
            bruto = "No entendí. ¿Podés reformularlo?"
        else:
            bruto = compuerta.ejecutar(intencion, contexto).mensaje
        respuesta = persona.estilizar(bruto)
        contexto.agregar(texto, respuesta)
        return respuesta

    return procesar


def construir_wakeword():
    """Detector de wake word, si hay un modelo entrenado. None si no lo hay: el asistente
    sigue funcionando con el hotkey."""
    cfg = (cargar_audio().get("wakeword") or {})
    modelo = cfg.get("modelo")
    if not modelo or not Path(modelo).exists():
        return None
    try:
        from adapters.wakeword import DetectorWakeWord
        det = DetectorWakeWord(
            modelo,
            umbral=float(cfg.get("umbral", 0.5)),
            refractario_s=float(cfg.get("refractario_s", 2.0)),
        )
        print(f"[wake word activo: {Path(modelo).stem} (umbral {cfg.get('umbral', 0.5)})]")
        return det
    except Exception as e:
        print(f"[wake word desactivado: {e}] Uso solo el hotkey.")
        return None


def correr_daemon(procesar, salida, auditor, persona_cfg: dict) -> None:
    """Modo residente: wake word + hotkey + bandeja + watchdog + residencia."""
    from adapters.input_voice import GrabadorContinuo
    from core.daemon import Daemon

    audio_cfg = cargar_audio()
    cap = audio_cfg.get("captura") or {}
    dae = audio_cfg.get("daemon") or {}

    grabador = GrabadorContinuo(
        sample_rate=int(cap.get("sample_rate", 16000)),
        bloque_ms=int(cap.get("bloque_ms", 100)),
        max_segundos=int(dae.get("max_segundos", 30)),
    )
    Daemon(
        construir_stt=construir_stt,          # se llama recién al despertar (warm-up)
        grabador=grabador,
        procesar=procesar,
        salida=salida,
        auditor=auditor,
        tecla=str(dae.get("tecla", "ctrl_r")),
        nombre=str(persona_cfg.get("nombre", "Asistente")),
        wakeword=construir_wakeword(),
        gracia_s=float(dae.get("gracia_s", 300)),
        silencio_ms=int(cap.get("silencio_ms", 1200)),
        umbral_silencio=float(cap.get("umbral_silencio", 0.015)),
        max_segundos=int(cap.get("max_segundos", 15)),
    ).correr()


def main() -> None:
    modo_voz = "--voz" in sys.argv
    modo_daemon = "--daemon" in sys.argv

    persona_cfg = cargar_persona()
    registry = cargar_skills()
    router = Router(registry)
    auditor = Auditor()
    compuerta = Compuerta(registry, auditor, confirmar=confirmar_por_consola)
    persona = Persona(persona_cfg)
    contexto = Contexto()
    salida = construir_salida(persona_cfg)
    procesar = construir_procesador(router, compuerta, persona, contexto)

    if modo_daemon:
        try:
            correr_daemon(procesar, salida, auditor, persona_cfg)
            return
        except Exception as e:
            print(f"[daemon desactivado: {e}] Caigo al REPL.")

    entrada = construir_entrada(modo_voz)
    print(f"Listo. {len(registry)} skills cargadas. Decí o escribí 'salir' para terminar.")
    while True:
        texto = entrada.leer()
        if texto is None or texto.strip().lower() in SALIDAS:
            salida.decir("Hasta luego.")
            break
        if not texto.strip():
            continue
        salida.decir(procesar(texto))


if __name__ == "__main__":
    main()
