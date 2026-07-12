# Wake word — "Raftalia"

Entrenamiento del detector que despierta al asistente. **Sin Docker**: todo corre en el
`.venv` del proyecto, en Windows.

## Por qué NO usamos Docker (aunque el pipeline "oficial" lo pide)

openWakeWord no clasifica audio crudo. Trae **dos modelos ONNX preentrenados**
(melspectrograma + embedding) que convierten 2 segundos de audio en una matriz de
**16×96**. Lo único que hay que entrenar es un **clasificador pequeño** sobre esas
features.

El pipeline oficial exige Python 3.10, PyTorch 1.13.1 y TensorFlow 2.8.1 (versiones de
2022) porque hace más cosas de las que necesitamos — y esas versiones son irreconciliables
con las librerías modernas: al instalarlas, pip termina subiendo numpy a 2.x y rompiendo
PyTorch 1.13. Es dependency hell puro, y no hace falta pasar por ahí.

También descartamos `piper-sample-generator`: su generador multi-hablante es **solo
inglés**, y su versión actual exige PyTorch 2, que choca con el 1.13 del pipeline oficial.
Para español no aporta nada que Piper no haga ya.

## Pasos

### 1. Descargar varias voces de Piper

M�s voces = más variedad tímbrica = mejor detector.

```bash
python -m piper.download_voices es_MX-ald-medium es_ES-davefx-medium \
    es_ES-sharvard-medium es_AR-daniela-high --download-dir voices
```

### 2. Grabar tus muestras

```bash
python scripts/grabar_wakeword.py                    # 40 positivas
python scripts/grabar_wakeword.py --negativas --n 20 # 20 parecidas que NO deben disparar
```

**Por qué grabar.** Las voces de Piper hablan con acento neutro de locutor. Vos no. Un
modelo entrenado solo con voces sintéticas se pone quisquilloso justo con vos, que sos el
único usuario. El síntoma no es que falle siempre: es que **funciona a veces**, y eso
frustra más. Tus grabaciones cierran esa brecha. Beneficio extra: también hace menos
probable que **otra persona** lo dispare.

### 3. Generar las muestras sintéticas

```bash
python scripts/generar_sinteticas.py
```

Produce tres conjuntos:

| Conjunto | Qué es | Para qué |
|---|---|---|
| `sinteticas_positivas` | "Raftalia" en N voces × velocidades × prosodias | El modelo aprende la palabra |
| `sinteticas_negativas` | "Rafa", "Natalia", "batalla", "raspa"... | Evita falsos positivos con palabras parecidas |
| `sinteticas_habla` | Frases normales en español | **Sin esto el detector dispara con cualquier conversación** |

### 4. Entrenar

```bash
python scripts/entrenar_wakeword.py
```

Sale un `.onnx` de ~800 KB en `wakeword/modelos/raftalia.onnx`. Con GPU tarda minutos.

### 5. Probar

```bash
python main.py --daemon
```

Decí «Raftalia».

## Ajustar (esto SIEMPRE hace falta la primera vez)

El umbral vive en `config/audio.yaml` → `wakeword.umbral`. Empezá en `0.5`.

| Síntoma | Ajuste |
|---|---|
| Te despierta solo (falsos positivos) | Subilo: `0.6` → `0.7` |
| No te reconoce | Bajalo: `0.4` → `0.35` |
| Tenés que bajar de `0.3` para que ande | El problema es el dataset: grabá más muestras y reentrená |

**El umbral es un dial; el entrenamiento es una fábrica.** No reentrenes para calibrar.

## Detalles técnicos

- **Ventana de 2 s con desplazamiento aleatorio.** En uso real, openWakeWord desliza una
  ventana sobre el audio: la palabra puede caer en cualquier posición. Si todas las
  muestras la tuvieran centrada, el detector fallaría en producción.
- **Las negativas pesan el doble en la pérdida.** Un falso positivo (te despierta solo)
  molesta más que un falso negativo (repetís la palabra).
- **Tus grabaciones se repiten más veces que las sintéticas** (20× vs 2×): son pocas pero
  son las que importan.
- **El texto es "Raftalia", no "Raphtalia".** El texto se pasa por espeak-ng para generar
  las voces sintéticas, así que hay que escribirlo como se pronuncia.
