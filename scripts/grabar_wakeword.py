"""Graba tus muestras del wake word, con control de calidad.

Por qué grabar: el pipeline de entrenamiento genera miles de muestras SINTÉTICAS con las
voces de Piper, que hablan con acento neutro de locutor. Vos no. El clasificador aprende
ese sonido sintético y después se pone quisquilloso justo con vos, que sos el único
usuario. El síntoma no es que falle siempre: es que funciona a veces. Y eso frustra más.

Tus muestras cierran esa brecha. Y como sesgan el modelo hacia TU voz, también hacen que
sea menos probable que otra persona lo dispare.

Uso (con el venv activo):
    python scripts/grabar_wakeword.py                 # 40 muestras positivas
    python scripts/grabar_wakeword.py --n 20          # cuántas
    python scripts/grabar_wakeword.py --negativas     # frases parecidas (NO deben disparar)

Las muestras salen en wakeword/muestras/positivas/ (o /negativas/), en WAV 16 kHz mono,
que es lo que espera openWakeWord.
"""
from __future__ import annotations

import argparse
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wakeword.calidad import evaluar, pico, rms   # noqa: E402

SAMPLE_RATE = 16000
DURACION_S = 2.0

# Variar las condiciones es lo que hace robusto al modelo. Un dataset donde siempre
# hablás igual, a la misma distancia y sin ruido, produce un detector frágil.
VARIACIONES = [
    "normal, a medio metro del micro",
    "un poco más cerca del micro",
    "más lejos (a un metro o más)",
    "más rápido de lo normal",
    "más lento, separando las sílabas",
    "más bajo, casi susurrando",
    "más fuerte, alzando la voz",
    "con música o la tele de fondo",
    "girado, sin mirar el micrófono",
    "como si preguntaras algo (tono ascendente)",
]

# Frases parecidas que NO deben despertar al asistente. Son las que más falsos positivos
# causan: el modelo necesita verlas explícitamente como negativas.
NEGATIVAS_SUGERIDAS = [
    "rafa", "rafael", "italia", "natalia", "batalla", "tafalla",
    "raptar", "raspa", "gramática", "aftalia", "rafta", "talia",
]


def grabar(segundos: float):
    import numpy as np
    import sounddevice as sd

    audio = sd.rec(int(segundos * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=1, dtype="float32")
    sd.wait()
    return audio[:, 0].copy()


def guardar_wav(audio, destino: Path) -> None:
    import numpy as np

    destino.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)                 # 16 bits
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())


def cuenta_regresiva() -> None:
    for n in (3, 2, 1):
        print(f"  {n}...", end="\r", flush=True)
        time.sleep(0.6)
    print("  ¡HABLÁ!   ", end="", flush=True)


def sesion(nombre: str, carpeta: Path, cantidad: int, negativas: bool) -> int:
    guardadas = 0
    intento = 0

    while guardadas < cantidad:
        if negativas:
            frase = NEGATIVAS_SUGERIDAS[guardadas % len(NEGATIVAS_SUGERIDAS)]
            consigna = f'decí «{frase}»'
        else:
            variacion = VARIACIONES[guardadas % len(VARIACIONES)]
            consigna = f'decí «{nombre}» — {variacion}'

        print(f"\n[{guardadas + 1}/{cantidad}] {consigna}")
        try:
            input("  Enter para grabar (o 'q' + Enter para salir): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        cuenta_regresiva()
        audio = grabar(DURACION_S)
        print("listo.")

        ok, motivo = evaluar(audio, SAMPLE_RATE)
        print(f"  pico={pico(audio):.2f}  rms={rms(audio):.3f}  → ", end="")

        if not ok:
            print(f"DESCARTADA: {motivo}")
            continue

        intento += 1
        destino = carpeta / f"{nombre.lower()}_{intento:03d}.wav"
        guardar_wav(audio, destino)
        guardadas += 1
        print(f"OK  ({destino.name})")

    return guardadas


def main() -> None:
    parser = argparse.ArgumentParser(description="Graba muestras del wake word.")
    parser.add_argument("--nombre", default="Raftalia", help="palabra a grabar")
    parser.add_argument("--n", type=int, default=40, help="cuántas muestras")
    parser.add_argument("--negativas", action="store_true",
                        help="graba frases parecidas que NO deben disparar")
    args = parser.parse_args()

    raiz = Path(__file__).resolve().parent.parent / "wakeword" / "muestras"
    carpeta = raiz / ("negativas" if args.negativas else "positivas")

    tipo = "NEGATIVAS (no deben disparar)" if args.negativas else "POSITIVAS"
    print(f"=== Grabando {args.n} muestras {tipo} ===")
    print(f"Micrófono: {SAMPLE_RATE} Hz mono · {DURACION_S}s por muestra")
    print("Variá la distancia, el tono y el ruido de fondo: es lo que hace robusto al modelo.\n")

    guardadas = sesion(args.nombre, carpeta, args.n, args.negativas)
    print(f"\n=== {guardadas} muestras guardadas en {carpeta} ===")
    if guardadas < args.n:
        print("Volvé a correr el script para completar las que faltan.")


if __name__ == "__main__":
    main()
