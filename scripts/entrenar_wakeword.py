"""Entrena el wake word. En Windows, con el .venv del proyecto. SIN DOCKER.

Por qué no hace falta Docker: openWakeWord trae dos ONNX preentrenados (melspectrograma +
embedding) que convierten audio en features de 16x96. Lo único que entrenamos es un
clasificador pequeño sobre esas features, y eso corre en PyTorch moderno sin problema.
El pipeline "oficial" exige PyTorch 1.13 y TensorFlow 2.8 (versiones de 2022) porque hace
más cosas de las que necesitamos.

Uso:
    python scripts/entrenar_wakeword.py
    python scripts/entrenar_wakeword.py --epocas 200 --repeticiones 30
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import yaml                                              # noqa: E402
from wakeword.dataset import extraer_features, preparar  # noqa: E402

MUESTRAS = RAIZ / "wakeword" / "muestras"


def wavs(carpeta: Path) -> list[Path]:
    return sorted(carpeta.glob("*.wav")) if carpeta.exists() else []


class WakeWordNet:
    """Se define adentro para no importar torch si solo se consulta el script."""


def construir_red(frames: int = 16, dims: int = 96, oculta: int = 128):
    import torch.nn as nn

    return nn.Sequential(
        nn.Flatten(),
        nn.Linear(frames * dims, oculta), nn.LayerNorm(oculta), nn.ReLU(), nn.Dropout(0.2),
        nn.Linear(oculta, oculta), nn.LayerNorm(oculta), nn.ReLU(), nn.Dropout(0.2),
        nn.Linear(oculta, 1), nn.Sigmoid(),
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Entrena el wake word (sin Docker).")
    p.add_argument("--config", default=str(RAIZ / "wakeword" / "entrenar.yml"))
    p.add_argument("--epocas", type=int, default=150)
    p.add_argument("--repeticiones", type=int, default=20,
                   help="cuántas variantes por muestra grabada (desplazamiento + ruido)")
    p.add_argument("--rep-sinteticas", type=int, default=2)
    args = p.parse_args()

    import torch
    import torch.nn as nn

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    nombre = cfg.get("model_name", "wakeword")

    print("=== Cargando muestras ===")
    pos_reales = wavs(MUESTRAS / "positivas")
    pos_sint = wavs(MUESTRAS / "sinteticas_positivas")
    neg_reales = wavs(MUESTRAS / "negativas")
    neg_sint = wavs(MUESTRAS / "sinteticas_negativas")
    neg_habla = wavs(MUESTRAS / "sinteticas_habla")

    print(f"  positivas: {len(pos_reales)} grabadas + {len(pos_sint)} sintéticas")
    print(f"  negativas: {len(neg_reales)} grabadas + {len(neg_sint)} parecidas "
          f"+ {len(neg_habla)} de habla general")

    if not pos_reales and not pos_sint:
        print("\nNo hay muestras positivas. Corré antes:")
        print("  python scripts/grabar_wakeword.py")
        print("  python scripts/generar_sinteticas.py")
        sys.exit(1)
    if not neg_reales and not neg_sint and not neg_habla:
        print("\n[!] Sin negativas el modelo va a disparar con cualquier cosa.")
        sys.exit(1)

    # Tus grabaciones se repiten MÁS que las sintéticas: son pocas pero son las que
    # cierran la brecha de acento, así que pesan más en el dataset.
    print("\n=== Preparando el dataset (ventana de 2s, desplazamiento aleatorio) ===")
    X_pos = np.concatenate([
        preparar(pos_reales, args.repeticiones, semilla=1),
        preparar(pos_sint, args.rep_sinteticas, semilla=2),
    ]) if (pos_reales or pos_sint) else np.zeros((0, 32000), dtype=np.int16)

    X_neg = np.concatenate([
        preparar(neg_reales, args.repeticiones, semilla=3),
        preparar(neg_sint, args.rep_sinteticas, semilla=4),
        preparar(neg_habla, args.rep_sinteticas, semilla=5),
    ]) if (neg_reales or neg_sint or neg_habla) else np.zeros((0, 32000), dtype=np.int16)

    print(f"  clips positivos: {len(X_pos)}")
    print(f"  clips negativos: {len(X_neg)}")

    print("\n=== Extrayendo features (melspectrograma + embedding) ===")
    F_pos = extraer_features(X_pos)
    F_neg = extraer_features(X_neg)
    print(f"  positivas: {F_pos.shape}")
    print(f"  negativas: {F_neg.shape}")

    X = torch.from_numpy(np.concatenate([F_pos, F_neg])).float()
    y = torch.cat([torch.ones(len(F_pos), 1), torch.zeros(len(F_neg), 1)])

    # Separar validación ANTES de entrenar: si no, no sabés si generalizó o memorizó.
    g = torch.Generator().manual_seed(0)
    orden = torch.randperm(len(X), generator=g)
    X, y = X[orden], y[orden]
    corte = int(len(X) * 0.85)
    Xtr, ytr, Xva, yva = X[:corte], y[:corte], X[corte:], y[corte:]

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n=== Entrenando en {dispositivo} ===")
    red = construir_red().to(dispositivo)
    Xtr, ytr, Xva, yva = (t.to(dispositivo) for t in (Xtr, ytr, Xva, yva))

    # Un falso positivo (te despierta solo) molesta más que un falso negativo (repetís
    # la palabra). Por eso las negativas pesan más en la pérdida.
    peso_neg = 2.0
    pesos = torch.where(ytr > 0.5, torch.tensor(1.0, device=dispositivo),
                        torch.tensor(peso_neg, device=dispositivo))
    opt = torch.optim.AdamW(red.parameters(), lr=1e-3, weight_decay=1e-4)
    lossf = nn.BCELoss(weight=pesos)

    mejor = 0.0
    mejor_estado = None
    for epoca in range(1, args.epocas + 1):
        red.train()
        opt.zero_grad()
        loss = lossf(red(Xtr), ytr)
        loss.backward()
        opt.step()

        if epoca % 10 == 0 or epoca == args.epocas:
            red.eval()
            with torch.no_grad():
                pv = red(Xva)
                acc = ((pv > 0.5).float() == yva).float().mean().item()
                # recall: de las veces que decís la palabra, cuántas detecta
                pos_mask = yva > 0.5
                rec = ((pv[pos_mask] > 0.5).float().mean().item()
                       if pos_mask.any() else 0.0)
                # falsos positivos: cuántas negativas dispararon
                neg_mask = ~pos_mask
                fp = ((pv[neg_mask] > 0.5).float().mean().item()
                      if neg_mask.any() else 0.0)
            print(f"  época {epoca:4d}  loss={loss.item():.4f}  "
                  f"acc={acc:.1%}  detección={rec:.1%}  falsos+={fp:.2%}")
            if acc > mejor:
                mejor = acc
                mejor_estado = {k: v.clone() for k, v in red.state_dict().items()}

    if mejor_estado is not None:
        red.load_state_dict(mejor_estado)

    salida = RAIZ / "wakeword" / "modelos"
    salida.mkdir(parents=True, exist_ok=True)
    destino = salida / f"{nombre}.onnx"

    red.eval().cpu()
    torch.onnx.export(red, torch.randn(1, 16, 96), str(destino),
                      input_names=["x"], output_names=["p"],
                      opset_version=13, dynamo=False)

    print(f"\n=== Listo: {destino} ({destino.stat().st_size // 1024} KB) ===")
    print(f"Mejor exactitud en validación: {mejor:.1%}")
    print("\nAhora:")
    print(f"  1. Verificá que config/audio.yaml apunte a wakeword/modelos/{nombre}.onnx")
    print("  2. python main.py --daemon")
    print("  3. Ajustá 'wakeword.umbral' (empezá en 0.5). NO reentrenes por esto.")


if __name__ == "__main__":
    main()
