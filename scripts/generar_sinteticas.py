"""Genera las muestras sintéticas del wake word (y de las frases negativas).

Corre en Windows, con el .venv del proyecto. NO necesita Docker.

Uso:
    # 1. Descargá varias voces en español (más voces = más variedad = mejor modelo)
    python -m piper.download_voices es_MX-ald-medium es_ES-davefx-medium \
        es_ES-sharvard-medium es_AR-daniela-high --download-dir voices

    # 2. Generá
    python scripts/generar_sinteticas.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import yaml                                    # noqa: E402
from wakeword.generar import generar           # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Genera muestras sintéticas del wake word.")
    p.add_argument("--config", default=str(RAIZ / "wakeword" / "entrenar.yml"))
    p.add_argument("--positivas", type=int, default=2000)
    p.add_argument("--negativas", type=int, default=2000)
    p.add_argument("--habla", type=int, default=2000,
                   help="clips de habla general en español (negativas de fondo)")
    args = p.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    voces = [str(RAIZ / v) for v in cfg["voces"]]
    disponibles = [v for v in voces if Path(v).exists()]
    if not disponibles:
        print("No hay voces de Piper. Descargalas primero:")
        print("  python -m piper.download_voices es_MX-ald-medium es_ES-davefx-medium "
              "es_ES-sharvard-medium --download-dir voices")
        sys.exit(1)

    print(f"Voces disponibles: {len(disponibles)}")
    for v in disponibles:
        print(f"  · {Path(v).stem}")
    if len(disponibles) < 3:
        print("\n  [!] Con menos de 3 voces la variedad es pobre. Descargá más.")

    base = RAIZ / "wakeword" / "muestras"

    print(f"\nGenerando {args.positivas} positivas ({cfg['target_phrase']})...")
    n = generar(cfg["target_phrase"], disponibles,
                base / "sinteticas_positivas", args.positivas)
    print(f"  {n} muestras en wakeword/muestras/sinteticas_positivas/")

    print(f"\nGenerando {args.negativas} negativas (frases parecidas)...")
    n = generar(cfg["custom_negative_phrases"], disponibles,
                base / "sinteticas_negativas", args.negativas)
    print(f"  {n} muestras en wakeword/muestras/sinteticas_negativas/")

    print(f"\nGenerando {args.habla} de habla general (negativas de fondo)...")
    n = generar(cfg["negative_speech"], disponibles,
                base / "sinteticas_habla", args.habla)
    print(f"  {n} muestras en wakeword/muestras/sinteticas_habla/")

    print("\nListo. Tus grabaciones reales siguen en muestras/positivas y "
          "muestras/negativas: todo se usa junto al entrenar.")


if __name__ == "__main__":
    main()
