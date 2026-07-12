"""Control de calidad de las muestras del wake word.

Un dataset con muestras saturadas, mudas o cortadas arruina el entrenamiento, y el
síntoma aparece recién al final: un modelo que "a veces" funciona. Se valida al grabar,
no después.

Funciones puras: se testean sin micrófono.
"""
from __future__ import annotations

import math

SATURACION = 0.98      # por encima de esto el micro recorta la onda y se pierde info
PICO_MINIMO = 0.05     # por debajo, la muestra es prácticamente inaudible
RMS_MINIMO = 0.008     # energía media mínima para considerar que hubo voz
VOZ_MINIMA_S = 0.25    # duración mínima de habla dentro de la muestra


def pico(audio) -> float:
    return max((abs(float(x)) for x in audio), default=0.0)


def rms(audio) -> float:
    n = len(audio)
    if n == 0:
        return 0.0
    return math.sqrt(sum(float(x) ** 2 for x in audio) / n)


def duracion_de_voz(audio, sample_rate: int, umbral: float = 0.02) -> float:
    """Segundos de audio con energía por encima del umbral. Detecta muestras donde
    hablaste demasiado tarde y el nombre quedó cortado."""
    activos = sum(1 for x in audio if abs(float(x)) > umbral)
    return activos / sample_rate if sample_rate else 0.0


def evaluar(audio, sample_rate: int) -> tuple[bool, str]:
    """(aceptada, motivo). El motivo es accionable: le dice al usuario QUÉ corregir."""
    if len(audio) == 0:
        return False, "no se grabó nada"

    p = pico(audio)
    if p >= SATURACION:
        return False, "saturada (te acercaste mucho o hablaste muy fuerte)"
    if p < PICO_MINIMO:
        return False, "casi muda (acercate al micro o hablá más fuerte)"
    if rms(audio) < RMS_MINIMO:
        return False, "muy débil"

    voz = duracion_de_voz(audio, sample_rate)
    if voz < VOZ_MINIMA_S:
        return False, "no detecté el nombre (¿hablaste a tiempo?)"

    return True, "ok"
