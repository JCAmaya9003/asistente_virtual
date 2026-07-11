"""Motor STT con faster-whisper (CUDA si está disponible, CPU si no).

Recibe audio como array numpy float32 mono a 16 kHz y devuelve texto. El audio vive en
RAM y nunca toca el disco (§2.3 del ARCHITECTURE.md).

Las funciones puras de arriba se testean sin micrófono ni GPU; la clase hace imports
perezosos para que la suite corra en cualquier máquina.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


# --------------------------------------------------------------------------- #
# Funciones puras (testeables sin hardware)
# --------------------------------------------------------------------------- #

def resolver_dispositivo(device: str, compute_type: str, cuda_disponible: bool) -> tuple[str, str]:
    """Traduce la config ('auto') a un (device, compute_type) concreto.

    int8_float16 en GPU: ~40% menos VRAM que float16 con pérdida de precisión
    despreciable. int8 en CPU es el único razonable.
    """
    if device == "auto":
        device = "cuda" if cuda_disponible else "cpu"
    if compute_type == "auto":
        compute_type = "int8_float16" if device == "cuda" else "int8"
    return device, compute_type


def construir_initial_prompt(nombres_apps: list[str]) -> str:
    """Sesga a Whisper hacia los nombres propios que el usuario va a decir.

    Sin esto, "abre Spotify" se transcribe como "abre espotifai". El initial_prompt le
    da a Whisper el vocabulario esperado (§7.3 del ARCHITECTURE.md).
    """
    if not nombres_apps:
        return ""
    listado = ", ".join(sorted({n.strip().title() for n in nombres_apps if n.strip()}))
    return f"Comandos para un asistente de voz. Aplicaciones: {listado}."


def limpiar_transcripcion(texto: str) -> str:
    """Normaliza la salida de Whisper antes de dársela al router.

    Whisper devuelve espacios al inicio, mayúsculas y puntuación final que el matcher
    no espera. El router compara en minúsculas y anclado al inicio.
    """
    texto = (texto or "").strip()
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.strip(" .,¡!¿?")
    return texto


# --------------------------------------------------------------------------- #
# Motor
# --------------------------------------------------------------------------- #

def _registrar_dlls_cuda_windows() -> None:
    """Las wheels nvidia-cublas-cu12 / nvidia-cudnn-cu12 instalan las DLLs dentro del
    venv, pero Windows no las busca ahí. Sin esto, faster-whisper falla al transcribir
    con 'Library cublas64_12.dll is not found'.

    Hay que hacer DOS cosas, no una:
      - add_dll_directory: sirve para las cargas que hace Python.
      - PATH: CTranslate2 carga cuBLAS/cuDNN de forma DIFERIDA (recién al codificar) con
        un LoadLibrary plano de C++, que ignora add_dll_directory y solo mira el orden de
        búsqueda estándar de Windows. Por eso el modelo carga bien y falla al transcribir.

    Ojo: 'nvidia' es un namespace package, así que nvidia.__file__ es None; la ruta real
    está en __path__. Nunca debe tumbar el arranque: si algo falla, se sigue sin CUDA.
    """
    if sys.platform != "win32":
        return
    try:
        import nvidia
        raices = [Path(p) for p in getattr(nvidia, "__path__", [])]
    except Exception:
        return

    for raiz in raices:
        for sub in ("cublas", "cudnn"):
            libdir = raiz / sub / "bin"
            if not libdir.is_dir():
                continue
            try:
                os.add_dll_directory(str(libdir))
            except OSError:
                pass
            # Imprescindible para la carga diferida de CTranslate2.
            os.environ["PATH"] = f"{libdir}{os.pathsep}{os.environ.get('PATH', '')}"


class WhisperEngine:
    def __init__(self, modelo: str = "large-v3", device: str = "auto",
                compute_type: str = "auto", idioma: str = "es",
                initial_prompt: str = "") -> None:
        _registrar_dlls_cuda_windows()
        from faster_whisper import WhisperModel

        self._idioma = idioma
        self._initial_prompt = initial_prompt or None

        dev, ct = resolver_dispositivo(device, compute_type, cuda_disponible=(device != "cpu"))
        try:
            self._model = WhisperModel(modelo, device=dev, compute_type=ct)
            self.dispositivo = dev
        except Exception as e:
            if dev == "cpu":
                raise
            # Degradación elegante: sin CUDA el asistente sigue oyendo, más lento.
            print(f"[stt] CUDA no disponible ({type(e).__name__}); uso CPU.")
            dev, ct = resolver_dispositivo("cpu", "auto", cuda_disponible=False)
            self._model = WhisperModel(modelo, device=dev, compute_type=ct)
            self.dispositivo = dev

    def transcribir(self, audio) -> str:
        """audio: numpy float32 mono a 16 kHz, en el rango [-1, 1]."""
        segmentos, _ = self._model.transcribe(
            audio,
            language=self._idioma,          # fijo: la autodetección falla en clips cortos
            initial_prompt=self._initial_prompt,
            vad_filter=True,                # descarta silencios dentro del clip
            beam_size=5,
        )
        return limpiar_transcripcion(" ".join(s.text for s in segmentos))
