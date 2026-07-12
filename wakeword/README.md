# Wake word — "Raftalia"

Entrenamiento del detector que despierta al asistente. Es la parte más frágil del
proyecto: el pipeline exige versiones de 2022 (Python 3.10, PyTorch 1.13.1, TF 2.8.1),
por eso vive en Docker y se construye **una sola vez**.

## Requisitos

- WSL2 + Docker con soporte de GPU. Verificar: `wsl -d Ubuntu-22.04 -- nvidia-smi`
- Las muestras ya grabadas (ver abajo).

## 1. Grabar tus muestras

```bash
python scripts/grabar_wakeword.py                    # 40 positivas
python scripts/grabar_wakeword.py --negativas --n 20 # 20 negativas
```

**Por qué grabar.** El pipeline genera miles de muestras sintéticas con las voces de
Piper, que hablan con acento neutro de locutor. Vos no. El clasificador aprende ese
sonido sintético y después se pone quisquilloso justo con vos, que sos el único usuario.
El síntoma no es que falle siempre: es que **funciona a veces**. Y eso frustra más que si
no funcionara nada.

En español el problema es peor que en inglés: el generador multi-hablante de Piper (que
mezcla speaker embeddings para producir cientos de voces distintas) **solo existe en
inglés**. En español la variación tímbrica de las muestras sintéticas es mucho menor.

Beneficio extra: un modelo sesgado hacia tu voz también **rechaza mejor a otras
personas**.

## 2. Construir el contenedor (una vez, tarda)

```bash
cd wakeword/docker
docker compose build
```

## 3. Entrenar

```bash
docker compose run --rm entrenador bash
# ya dentro del contenedor:
cd /work/openWakeWord/notebooks
python train.py --training_config /work/wakeword/entrenar.yml
```

La primera corrida descarga ~4 GB de datos de entrenamiento (ruido de fondo y respuestas
de impulso de sala). Quedan cacheados en un volumen de Docker: no se vuelven a bajar.

El resultado es un `.onnx` de ~200 KB en `wakeword/modelos/`.

## Notas de esta máquina

- **`batch_size: 8`** en `entrenar.yml`. Con 4 GB de VRAM (RTX 3050) un batch grande
  revienta. En una GPU de 11 GB se usaría 100.
- El texto entrenado es **"Raftalia"**, no "Raphtalia": el pipeline pasa el texto por
  espeak-ng para generar las voces, así que hay que escribirlo como se pronuncia.

## Ajustar después de entrenar

El umbral de detección se afina en `config/audio.yaml` (`wakeword.umbral`), no
reentrenando. Empezá en `0.5`:

- Muchos falsos positivos (te despierta solo) → subilo a `0.6`–`0.7`.
- No te reconoce → bajalo a `0.4`–`0.35`.

Si tenés que bajar de `0.3` para que funcione, el problema es el dataset: grabá más
muestras positivas y reentrená.
