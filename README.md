# Asistente virtual local

Asistente de voz local para Windows: **vive en la bandeja del sistema**. Mantenés una
tecla, le hablás, y ejecuta acciones sobre la máquina respondiéndote con voz. Nada sale
del equipo. Privado, reversible y construido por fases.

> **Versión actual: v4 — wake word.**
> Decís «Raftalia» y responde. El hotkey sigue funcionando como respaldo.
> Whisper solo ocupa VRAM cuando hace falta: dormido, el asistente usa ~80 MB de RAM y 0 GB de VRAM.

---

## 1. Qué hace esta versión

**Tres modos, el mismo núcleo detrás:**

| Comando | Modo |
|---|---|
| `python main.py` | REPL de texto: escribís, te responde con voz |
| `python main.py --voz` | Push-to-talk en la terminal (Enter, hablás) |
| `python main.py --daemon` | **Residente**: vive en la bandeja, hotkey global |

**Funciona:**

- **Wake word**: decí «Raftalia» y te contesta «¿Sí?». Corre siempre en CPU con un modelo
  ONNX de ~200 KB (~80 MB de RAM, 2-3% de un núcleo, **cero VRAM**).
- **Estados de residencia**: Whisper sube a la GPU solo cuando hace falta, y con
  **warm-up especulativo** — empieza a cargar en cuanto disparás el wake word, mientras
  todavía estás diciendo el comando. Tras 5 minutos sin uso, libera la VRAM.
- **Hotkey global** (Ctrl derecho por defecto): mantenelo apretado, hablá, soltá. Funciona
  aunque la ventana no tenga el foco, y sigue disponible como respaldo del wake word.
- **Ícono de bandeja**: ves si está escuchando, podés pausarlo o salir.
- **Watchdog de audio**: detecta que el micrófono murió (audífonos desconectados,
  suspensión de Windows) y **reabre el stream solo**. Late en el audit log cada 5 minutos.
- **Arranque automático** al iniciar sesión, vía Task Scheduler (que lo relanza si crashea).
- **Oído**: faster-whisper `large-v3` en GPU (CUDA), cae a CPU si no hay. El audio vive en
  RAM y **nunca toca el disco**.
- **Voz**: responde hablando (Piper, local, español).
- **4 skills**:
  - `hora` — *("qué hora es")*
  - `abrir_app` — abre apps del whitelist, **con alias**: "abre google", "abrime chrome",
    "abre el navegador" → la misma app.
  - `nota` — anota texto dentro de la jaula de rutas. *("tomá nota comprar pan")*
  - `clima` — placeholder; declara permiso de red pero no está implementada.
- **Seguridad activa**: compuerta de ejecución, permisos declarativos, jaula de rutas
  (rechaza `..`, UNC, ADS, symlinks) y log de auditoría en JSONL.
- **Degradación elegante en toda la cadena**: sin Piper responde por consola; sin CUDA
  transcribe en CPU; sin micrófono cae al REPL de texto.

**Todavía no:**

- El router usa coincidencia de frases, no un LLM: solo entiende el catálogo. → v5
- No hace nada por su cuenta (sin automatizaciones). → v6

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
# Esperado: 86 passed, 1 skipped
# (el test de symlink se salta en Windows: crearlos exige permisos de admin)

# 5. Arrancar
python main.py --daemon
```

La primera vez, **descarga el modelo Whisper `large-v3` (~1.5 GB)**. Tarda varios minutos
y queda cacheado. Los warnings de `HF_TOKEN` y de symlinks son inofensivos.

Cuando veas `[Raftalia] activo`, **decí «Raftalia»** (o mantené Ctrl derecho y hablá).

Sin el modelo de wake word entrenado, el asistente funciona igual con el hotkey. Para
entrenarlo, ver **[`wakeword/README.md`](wakeword/README.md)**.

**Cada vez que abrás una terminal nueva**, activá el entorno: `.venv\Scripts\activate`

### Que arranque solo al iniciar sesión

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_autostart.ps1
```

No requiere permisos de administrador. Usa `pythonw.exe`, así no deja una consola abierta.
Para quitarlo: `Unregister-ScheduledTask -TaskName "AsistenteVirtual" -Confirm:$false`

---

## 3. Configuración

### Aplicaciones (`config/apps.yaml`)

Cada app declara **alias** (todos los nombres con los que la llamás) y un **destino**:

```yaml
chrome:
  alias: [google, navegador, el navegador]
  destino: C:\Program Files\Google\Chrome\Application\chrome.exe

discord:
  alias: [discor]
  # Discord cambia de carpeta en cada actualización: Update.exe siempre lanza la actual.
  destino: C:\Users\TU_USUARIO\AppData\Local\Discord\Update.exe --processStart Discord.exe

whatsapp:
  alias: [wasap, guasap]
  destino: whatsapp://          # apps de la Store: se abren por protocolo
```

El destino puede ser un `.exe`, un protocolo (`whatsapp://`) o un `shell:AppsFolder\...`.
Los alias también se le pasan a Whisper como pista, para que transcriba "Chrome" y no
"crom".

### Notas (`config/permisos.yaml`)

```yaml
nota: ["C:\\Users\\TU_USUARIO\\Documents\\notas"]
```

### Voz (`config/persona.yaml`)

`length_scale` a `1.2` habla más lento, `0.9` más rápido. `modelo` acepta cualquier voz de
[piper-samples](https://rhasspy.github.io/piper-samples).

### Oído y daemon (`config/audio.yaml`)

| Problema | Ajuste |
|---|---|
| Querés otra tecla | `daemon.tecla`: `f9`, `pause`, `scroll_lock`, `alt_r`... |
| (modo `--voz`) te corta antes de terminar | Subí `silencio_ms` a `1800` |
| (modo `--voz`) nunca corta, micro ruidoso | Subí `umbral_silencio` a `0.03` |
| No tenés GPU | `device: "cpu"` y `modelo: "small"` |
| El wake word te despierta solo | Subí `wakeword.umbral` a `0.6`–`0.7` |
| El wake word no te reconoce | Bajá `wakeword.umbral` a `0.4`. Si tenés que bajar de `0.3`, grabá más muestras y reentrená |

---

## 4. Idea del proyecto

La voz es un **adaptador de entrada/salida**. El proyecto real es el **registro de skills**
+ el **router de intenciones** + la **compuerta de seguridad**. Todo lo demás se enchufa
alrededor de ese núcleo sin tocarlo. Por eso el sistema completo se construyó (v0) antes de
tocar audio, y por eso los 71 tests corren **sin micrófono, sin parlantes y sin GPU**.

```
core/            # el núcleo estable (no cambia entre versiones)
  skill.py         # contrato base de Skill + Permisos + Resultado
  registry.py      # descubre y registra skills automáticamente
  router.py        # texto → Intencion (v3: matcher anclado; v5: + LLM)
  gate.py          # compuerta: valida, confirma, ejecuta, audita
  sandbox.py       # jaula de rutas
  audit.py         # log append-only en JSONL
  watchdog.py      # detecta el micrófono muerto y reabre el stream
  residencia.py    # dormido → despertando (warm-up) → activo → enfriando
  daemon.py        # modo residente: wake word + hotkey + bandeja + watchdog
  contexto.py      # últimos N turnos + flags de confianza
  config.py        # carga de los YAML
  persona.py       # capa de estilo pre-voz
skills/          # acciones concretas (agregar una NO toca core/)
adapters/        # capa de entrada/salida intercambiable
  input_cli.py / output_console.py   # teclado y consola
  input_voice.py / stt_whisper.py    # micrófono (faster-whisper)
  output_tts.py / tts_piper.py       # voz (Piper)
  hotkey.py / tray.py                # hotkey global y bandeja
  wakeword.py                        # detector openWakeWord (siempre activo, en CPU)
config/          # apps.yaml, permisos.yaml, persona.yaml, audio.yaml
wakeword/        # entrenamiento del wake word (Docker) + muestras + modelos
scripts/         # install_autostart.ps1, grabar_wakeword.py
tests/           # golden set, jaula, persona, oído, watchdog, alias de apps
docs/            # ARCHITECTURE.md y ROADMAP.md (el plano completo)
main.py          # punto de entrada
```

### Principios

- **Núcleo + adaptadores.** El núcleo no sabe si el input vino del teclado o del micrófono.
- **Seguridad desde el día uno.** Retrofitear seguridad no ocurre nunca.
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

## 5. Problemas comunes

| Síntoma | Causa | Solución |
|---|---|---|
| `No module named pytest` / `piper` / `faster_whisper` | El venv no está activo | `.venv\Scripts\activate` y `pip install -r requirements.txt` |
| `RuntimeError: Library cublas64_12.dll is not found` | Windows no busca las DLLs de CUDA dentro del venv | Ver abajo ⬇ |
| `expected str... not NoneType` al cargar el oído | Mismo problema de CUDA | Ver abajo ⬇ |
| `[oído activo: ... en cpu]` teniendo GPU | Faltan las wheels de NVIDIA | `pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10"` |
| `[voz desactivada: configurá 'voz.modelo'...]` | Falta el modelo de Piper | Correr el paso 3 |
| El hotkey no responde | Otra app se robó la tecla | Cambiá `daemon.tecla` en `config/audio.yaml` |
| `ModuleNotFoundError: No module named 'core'` | Se ejecutó desde otra carpeta | Correr **desde la raíz** del repo |
| Errores raros de permisos | El proyecto está en OneDrive y sincroniza el `.venv` | Pausar OneDrive para esa carpeta |

### La trampa de las DLLs de CUDA (Windows)

El error más caro de este proyecto. Las wheels `nvidia-cublas-cu12` y `nvidia-cudnn-cu12`
instalan las DLLs **dentro del venv**, pero Windows no las busca ahí. Lo resuelve
`_registrar_dlls_cuda_windows()` en `adapters/stt_whisper.py`, y hay que hacer **dos**
cosas, no una:

1. `os.add_dll_directory(...)` — cubre las cargas que hace Python.
2. **Agregar la carpeta al `PATH` del proceso** — CTranslate2 carga cuBLAS de forma
   *diferida*, recién al codificar audio, con un `LoadLibrary` plano de C++ que **ignora**
   `add_dll_directory`. Por eso el modelo carga bien y falla al transcribir.

Además: `nvidia` es un *namespace package*, así que `nvidia.__file__` es `None`. La ruta
real está en `nvidia.__path__`.

---

## 6. Hoja de ruta

`v0` núcleo · `v0.5` jaula de archivos · `v1` voz de salida · `v2` micrófono ·
`v3` residente · **`v4` wake word ← estás acá** · `v5` router con LLM · `v6` automatizaciones

Detalle completo en `docs/ROADMAP.md`. Arquitectura, modelo de seguridad, presupuestos de
latencia/VRAM y decisiones técnicas (ADR) en `docs/ARCHITECTURE.md`.

## Licencia y créditos

Voz: [Piper](https://github.com/OHF-Voice/piper1-gpl) (GPL-3.0).
Oído: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT).
Wake word: [openWakeWord](https://github.com/dscripka/openWakeWord) (Apache-2.0).
Todos locales y offline.
