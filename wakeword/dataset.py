"""Construcción del dataset para entrenar el wake word.

openWakeWord no clasifica audio crudo: usa dos modelos ONNX preentrenados (melspectrograma
+ embedding) que convierten 2 segundos de audio en una matriz de 16x96. El clasificador que
entrenamos solo ve esas features. Por eso NO hace falta Docker ni PyTorch 1.13: los
extractores vienen con el paquete y corren en onnxruntime moderno.

DECISIONES QUE IMPORTAN
-----------------------
1. VENTANA FIJA DE 2 SEGUNDOS. Es lo que produce exactamente (16, 96), la entrada que
   espera openWakeWord.

2. DESPLAZAMIENTO ALEATORIO. En uso real, openWakeWord desliza una ventana sobre el audio:
   la palabra puede caer al principio, al medio o al final. Si todas las muestras de
   entrenamiento tuvieran la palabra centrada, el detector fallaría en producción. Por eso
   cada muestra se ubica en un punto aleatorio de la ventana.

3. AUMENTACIÓN. Ruido y ganancia variable, para que el modelo funcione en un cuarto real
   y no solo en condiciones de laboratorio.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 16000
VENTANA = 2 * SR          # 32000 muestras = 2 s = features (16, 96)


def leer_wav(ruta: Path) -> np.ndarray:
    """WAV → float32 mono en [-1, 1]. Remuestrea groseramente si hace falta."""
    with wave.open(str(ruta), "rb") as w:
        n = w.getnframes()
        crudo = w.readframes(n)
        canales = w.getnchannels()
        sr = w.getframerate()
    audio = np.frombuffer(crudo, dtype=np.int16).astype(np.float32) / 32768.0
    if canales > 1:
        audio = audio.reshape(-1, canales).mean(axis=1)
    if sr != SR:                                   # remuestreo lineal simple
        n_nuevo = int(len(audio) * SR / sr)
        audio = np.interp(np.linspace(0, len(audio) - 1, n_nuevo),
                          np.arange(len(audio)), audio).astype(np.float32)
    return audio


def encajar(audio: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Lleva el audio a exactamente 2 s, ubicándolo en un punto ALEATORIO de la ventana.

    Esto es lo que enseña al modelo a detectar la palabra sin importar dónde caiga dentro
    de la ventana deslizante. Sin esto, el detector solo funciona si hablás justo a tiempo.
    """
    if len(audio) >= VENTANA:
        inicio = rng.integers(0, len(audio) - VENTANA + 1)
        return audio[inicio:inicio + VENTANA]

    ventana = np.zeros(VENTANA, dtype=np.float32)
    offset = int(rng.integers(0, VENTANA - len(audio) + 1))
    ventana[offset:offset + len(audio)] = audio
    return ventana


def aumentar(audio: np.ndarray, rng: np.random.Generator,
             ruido: float = 0.02, ganancia: tuple[float, float] = (0.5, 1.4)) -> np.ndarray:
    """Ruido blanco + ganancia aleatoria. Simula micrófonos y ambientes distintos."""
    audio = audio * rng.uniform(*ganancia)
    audio = audio + rng.normal(0, rng.uniform(0, ruido), size=len(audio)).astype(np.float32)
    return np.clip(audio, -1.0, 1.0).astype(np.float32)


def a_int16(audio: np.ndarray) -> np.ndarray:
    """openWakeWord espera int16."""
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)


def preparar(rutas: list[Path], repeticiones: int, semilla: int = 0,
             con_aumento: bool = True) -> np.ndarray:
    """Lee los WAV y devuelve un lote (N, 32000) int16 listo para extraer features.

    'repeticiones' multiplica el dataset: cada archivo aparece varias veces con distinto
    desplazamiento y aumentación. Es la forma barata de tener más datos de tus 40 muestras.
    """
    rng = np.random.default_rng(semilla)
    lote = []
    for ruta in rutas:
        try:
            audio = leer_wav(ruta)
        except Exception:
            continue
        for _ in range(repeticiones):
            x = encajar(audio, rng)
            if con_aumento:
                x = aumentar(x, rng)
            lote.append(a_int16(x))
    if not lote:
        return np.zeros((0, VENTANA), dtype=np.int16)
    return np.stack(lote)


def extraer_features(lote: np.ndarray, batch_size: int = 128) -> np.ndarray:
    """(N, 32000) int16 → (N, 16, 96) float32, con los ONNX de openWakeWord."""
    from openwakeword.utils import AudioFeatures

    if len(lote) == 0:
        return np.zeros((0, 16, 96), dtype=np.float32)
    return AudioFeatures().embed_clips(lote, batch_size=batch_size)
