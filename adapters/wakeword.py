"""Detector de wake word (openWakeWord). Corre SIEMPRE, en CPU, con consumo despreciable.

El modelo es un ONNX de ~200 KB que hace inferencia sobre frames de 80 ms. Es lo único
que está vivo mientras el asistente duerme: ~80 MB de RAM y 2-3% de un núcleo. Cero VRAM.

Import perezoso: sin el modelo entrenado, el asistente sigue funcionando con el hotkey.
"""
from __future__ import annotations

from pathlib import Path

# openWakeWord espera bloques de 1280 muestras a 16 kHz = 80 ms.
FRAME = 1280


class DetectorWakeWord:
    def __init__(self, modelo: str | Path, umbral: float = 0.5,
                 refractario_s: float = 2.0) -> None:
        from openwakeword.model import Model

        # OJO: el parámetro es wakeword_model_paths (verificado contra la API real).
        self._modelo = Model(wakeword_model_paths=[str(modelo)])
        self._nombre = Path(modelo).stem
        self._umbral = umbral
        self._refractario = refractario_s
        self._ultimo_disparo = 0.0

    def procesar(self, frame, ahora: float) -> bool:
        """frame: 1280 muestras int16. True si detectó el wake word.

        El período refractario evita que una sola pronunciación dispare varias veces:
        el modelo emite score alto durante varios frames seguidos.
        """
        if ahora - self._ultimo_disparo < self._refractario:
            return False

        scores = self._modelo.predict(frame)
        score = max(scores.values()) if scores else 0.0
        if score >= self._umbral:
            self._ultimo_disparo = ahora
            return True
        return False

    def reset(self) -> None:
        """Limpia el buffer interno. Se llama al terminar de atender un comando, para
        que el audio de la interacción no contamine la siguiente detección."""
        try:
            self._modelo.reset()
        except Exception:
            pass
