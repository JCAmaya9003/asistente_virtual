# Asistente virtual local

Asistente de voz local para Windows: **lo escuchás hablar y él te escucha a vos**. Ejecuta
acciones acotadas sobre la máquina, sin que nada salga del equipo. Privado, reversible y
construido por fases.

> **Versión actual: v2 — el asistente escucha.**
> Push-to-talk: apretás Enter, hablás, te responde con voz. El wake word llega en la v4.

---

## 1. Qué hace esta versión

**Funciona:**

- **Dos modos de entrada**, misma lógica detrás:
  - `python main.py` → escribís por teclado.
  - `python main.py --voz` → **hablás por micrófono** (push-to-talk).
- **Voz de salida**: te responde hablando (Piper, local, español).
- **Oído**: transcribe con faster-whisper `large-v3` en GPU (CUDA), y cae a CPU si no hay.
  El audio vive en RAM y **nunca toca el disco**.
- **4 skills**:
  - `hora` — te dice la hora. *("qué hora es")*
  - `abrir_app` — abre una app del whitelist. *("abre spotify")*
  - `nota` — anota texto dentro de la jaula de rutas. *("tomá nota comprar pan")*
  - `clima` — placeholder; declara permiso de red pero aún no está implementada.
- **Seguridad activa**: compuerta de ejecución, permisos declarativos por skill, jaula de
  rutas (rechaza `..`, UNC, ADS y symlinks que escapan) y log de auditoría en JSONL.
- **Router anclado**: exige que la orden empiece con una frase conocida. Fallar cerrado
  ("no entendí") es mejor que ejecutar la skill equivocada.
- **Degradación elegante en toda la cadena**: sin modelo Piper responde por consola; sin
  CUDA transcribe en CPU; sin micrófono o sin faster-whisper, cae al REPL de texto.

**Todavía no:**

- No tiene wake word ni corre en segundo plano: hay que arrancarlo a mano. → v3 y v4
- El router usa coincidencia de frases, no un LLM: órdenes fuera del catálogo no las
  entiende. → v5

---

## 2. Puesta en marcha (desde cero, en cualquier máquina)

**Requisitos:** Windows 10/11, **Python 3.11 de python.org** (no el de MSYS2 ni el de la
Microsoft Store: sus librerías nativas dan problemas). GPU NVIDIA opcional pero muy
recomendable.

```bash
# 0. Instalar Python 3.11 si no está
winget install Python.Python.3.11
# (cerrá y reabrí la terminal después de instalar)

# 1. Entorno virtual aislado
py -3.11 -m venv .venv
.venv\Scripts\activate
# El prompt debe mostrar (.venv) al inicio. Si no lo ves, no sigas.

# 2. Dependencias (incluye las librerías CUDA; son varios cientos de MB)
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. Descargar una voz en español (~60 MB, no se versiona)
python -m piper.download_voices es_MX-ald-medium --download-dir voices

# 4. Verificar que todo está sano
python -m pytest -q
# Esperado: 49 passed, 1 skipped
# (el test de symlink se salta en Windows: crearlos exige permisos de admin)

# 5. Arrancar
python main.py         # modo teclado
python main.py --voz   # modo micrófono
```

La primera vez que corras `--voz`, **descarga el modelo Whisper `large-v3` (~1.5 GB)**.
Tarda varios minutos y queda cacheado. Los warnings de `HF_TOKEN` y de symlinks son
inofensivos: ignoralos.

**Cada vez que abrás una terminal nueva**, activá el entorno: `.venv\Scripts\activate`

### Probarlo

Modo teclado:

```
qué hora es           → te responde con voz
abre spotify          → pedirá que agregues la app a apps.yaml
tomá nota comprar pan → pedirá que configures la carpeta de notas
salir
```

Modo `--voz`: Enter → hablás → corta solo al detectar silencio → te muestra `[oí]: ...` y
ejecuta. También podés escribir el comando en vez de hablarlo (útil para depurar).

### Habilitar las skills que necesitan configuración

- **`abrir_app`** → en `config/apps.yaml`, mapeá nombre a ruta del ejecutable:
  ```yaml
  spotify: C:\Users\TU_USUARIO\AppData\Roaming\Spotify\Spotify.exe
  ```
  Los nombres de este archivo también se le pasan a Whisper como `initial_prompt`, para
  que transcriba "Spotify" y no "espotifai".

- **`nota`** → en `config/permisos.yaml`, declará la carpeta permitida:
  ```yaml
  nota: ["C:\\Users\\TU_USUARIO\\Documents\\notas"]
  ```

### Ajustes

**Voz** (`config/persona.yaml` → `voz`): `length_scale` a `1.2` habla más lento, `0.9` más
rápido. Podés cambiar `modelo` por otra voz de
[piper-samples](https://rhasspy.github.io/piper-samples).

**Oído** (`config/audio.yaml`):

| Problema | Ajuste |
|---|---|
| Te corta antes de que termines de hablar | Subí `silencio_ms` a `1800` |
| Nunca corta (micro ruidoso) | Subí `umbral_silencio` a `0.03` |
| No tenés GPU | Poné `device: "cpu"` y `modelo: "small"` |

---

## 3. Idea del proyecto

La voz es un **adaptador de entrada/salida**. El proyecto real es el **registro de skills**
+ el **router de intenciones** + la **compuerta de seguridad**. Todo lo demás se enchufa
alrededor de ese núcleo sin tocarlo. Por eso el sistema completo se construyó (v0) antes
de tocar audio, y por eso los 50 tests corren **sin micrófono, sin parlantes y sin GPU**.

```
core/            # el núcleo estable (no cambia entre versiones)
  skill.py         # contrato base de Skill + Permisos + Resultado
  registry.py      # descubre y registra skills automáticamente
  router.py        # texto → Intencion (v2: matcher anclado; v5: + LLM)
  gate.py          # compuerta: valida, confirma, ejecuta, audita
  sandbox.py       # jaula de rutas
  audit.py         # log append-only en JSONL
  contexto.py      # últimos N turnos + flags de confianza
  config.py        # carga de los YAML
  persona.py       # capa de estilo pre-voz
skills/          # acciones concretas (agregar una NO toca core/)
adapters/        # capa de entrada/salida intercambiable
  input_cli.py / output_console.py   # teclado y consola
  input_voice.py / stt_whisper.py    # micrófono (faster-whisper)
  output_tts.py / tts_piper.py       # voz (Piper)
config/          # apps.yaml, permisos.yaml, persona.yaml, audio.yaml, .env.example
tests/           # golden set del router, jaula, persona, lógica del oído
docs/            # ARCHITECTURE.md y ROADMAP.md (el plano completo)
main.py          # punto de entrada
```

### Principios

- **Núcleo + adaptadores.** El núcleo no sabe si el input vino del teclado o del micrófono.
- **Seguridad desde el día uno.** La compuerta, los permisos y el audit log no son una fase
  posterior: retrofitear seguridad no ocurre nunca.
- **El router nunca emite comandos**, solo intenciones estructuradas. Whitelist, jamás
  blacklist. Ante la duda, "no entendí".
- **Nada se borra** (papelera, no borrado) y **nunca corre como administrador**.
- **Ninguna prueba toca hardware.** Si hay que hablarle para probar el router, la
  arquitectura está acoplada.

### Agregar una skill

Copiá el patrón de `skills/hora.py`: subclase de `Skill`, definí `nombre`, `descripcion`
(en inglés, para el LLM de la v5), `frases`, `permisos`, e implementá `ejecutar()`. El
registry la descubre sola. Son ~15 líneas y no se toca `core/`.

---

## 4. Problemas comunes

| Síntoma | Causa | Solución |
|---|---|---|
| `No module named pytest` / `piper` / `faster_whisper` | El venv no está activo, o faltan dependencias | `.venv\Scripts\activate` y `pip install -r requirements.txt` |
| `RuntimeError: Library cublas64_12.dll is not found` | Windows no busca las DLLs de CUDA dentro del venv | Ver abajo ⬇ |
| `[voz desactivada: configurá 'voz.modelo'...]` | Falta el modelo de Piper | Correr el paso 3 |
| `[oído activo: ... en cpu]` cuando tenés GPU | Faltan las wheels de NVIDIA | `pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10"` |
| `ModuleNotFoundError: No module named 'core'` | Se ejecutó desde otra carpeta | Correr `python main.py` **desde la raíz** del repo |
| Errores raros de permisos o archivos | El proyecto está en OneDrive y sincroniza el `.venv` | Pausar OneDrive para esa carpeta |

### La trampa de las DLLs de CUDA (Windows)

El error más caro de este proyecto. Las wheels `nvidia-cublas-cu12` y `nvidia-cudnn-cu12`
instalan las DLLs **dentro del venv**, pero Windows no las busca ahí. Lo resuelve
`_registrar_dlls_cuda_windows()` en `adapters/stt_whisper.py`, y hay que hacer **dos**
cosas, no una:

1. `os.add_dll_directory(...)` — cubre las cargas que hace Python.
2. **Agregar la carpeta al `PATH` del proceso** — CTranslate2 carga cuBLAS de forma
   *diferida*, recién al codificar audio, con un `LoadLibrary` plano de C++ que **ignora**
   `add_dll_directory`. Por eso el modelo carga bien y falla al transcribir.

Detalle adicional: `nvidia` es un *namespace package*, así que `nvidia.__file__` es `None`.
La ruta real está en `nvidia.__path__`.

---

## 5. Hoja de ruta

`v0` núcleo · `v0.5` jaula de archivos · `v1` voz de salida · **`v2` micrófono ← estás acá** ·
`v3` bandeja y autostart · `v4` wake word · `v5` router con LLM · `v6` automatizaciones

Detalle completo en `docs/ROADMAP.md`. Arquitectura, modelo de seguridad, presupuestos de
latencia/VRAM y decisiones técnicas (ADR) en `docs/ARCHITECTURE.md`.

## Licencia y créditos

Voz: [Piper](https://github.com/OHF-Voice/piper1-gpl) (GPL-3.0).
Oído: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT).
Ambos locales y offline.
