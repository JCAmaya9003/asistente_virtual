"""Motor TTS con Piper (local, CPU o CUDA). Sintetiza texto → audio WAV en bytes.

NO reproduce el audio: de eso se encarga SalidaTTS. Así el motor es intercambiable y se
puede probar sin hardware de audio. Cumple la interfaz TTSEngine de adapters/output_tts.

Nota de licencia: Piper es GPL-3.0. Perfecto para un proyecto open-source de portafolio.
Si algún día cerrás el código para comercializarlo, reevaluá el motor de voz.
"""
from __future__ import annotations

import io
import wave
from pathlib import Path

from piper import PiperVoice, SynthesisConfig


class PiperEngine:
    def __init__(self, modelo: str | Path, use_cuda: bool = False,
                length_scale: float = 1.0) -> None:
        # PiperVoice.load busca el .onnx.json junto al .onnx automáticamente.
        self._voice = PiperVoice.load(str(modelo), use_cuda=use_cuda)
        self._config = SynthesisConfig(length_scale=length_scale)

    def sintetizar_wav(self, texto: str) -> bytes:
        """Devuelve un WAV completo en memoria (nada toca el disco)."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            self._voice.synthesize_wav(texto, wav, syn_config=self._config)
        return buf.getvalue()