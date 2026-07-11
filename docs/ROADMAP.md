# Roadmap

Cada versión es utilizable por sí sola. Ninguna versión depende de la siguiente para
tener sentido. Si el proyecto se abandona en cualquier punto, lo construido sirve.

**Principio rector:** la seguridad no es una fase. Va desde la v0.

---

## v0 — El núcleo, sin voz

Un REPL en la terminal. Se escribe `hora`, `abre spotify`, `clima`.

- `core/skill.py`, `core/registry.py`, `core/router.py` (solo matcher de frases)
- `core/gate.py` — compuerta de ejecución completa
- `core/audit.py` — log JSONL append-only
- Tres skills: `hora`, `abrir_app`, `clima`
- Manifiesto de permisos en cada skill

**Terminado cuando:**
- [ ] Una skill nueva se agrega en ~15 líneas sin tocar `core/`
- [ ] Toda ejecución y todo rechazo aparecen en el log
- [ ] El golden set (versión corta, ~20 frases) pasa al 100 %
- [ ] `tests/` corre sin hardware

**Rama:** `feature/core-skills`

---

## v0.5 — Archivos y jaula

La primera skill que toca el disco. Aquí se prueba el modelo de seguridad de verdad.

- `core/sandbox.py` — resolución de path real, raíces permitidas
- `config/apps.yaml` + descubrimiento de `.lnk` del menú de inicio con aprobación manual
- `send2trash` como única forma de "borrar"
- Modo `--dry-run`

**Terminado cuando:**
- [ ] `tests/test_sandbox.py` rechaza `..`, UNC, symlinks, mayúsculas y ADS
- [ ] Ninguna ruta de código llama a `os.remove` ni a `shutil.rmtree`
- [ ] El descubrimiento de apps nunca escribe en `apps.yaml` sin aprobación

**Rama:** `feature/filesystem-sandbox`

---

## v1 — Que hable

- `io/output_tts.py` con la interfaz `TTSEngine`
- Piper, voz neutral en español
- `core/persona.py` — capa de estilo con perfil en `config/persona.yaml`

Se sigue escribiendo por teclado. Ya contesta hablando. Es la versión que motiva.

**Terminado cuando:**
- [ ] Cambiar de motor TTS es cambiar una línea de config
- [ ] El primer chunk de audio sale en < 300 ms
- [ ] La capa de persona se puede desactivar sin romper nada

**Rama:** `feature/tts-output`

---

## v2 — Que escuche (push-to-talk)

Una tecla, se graba, `faster-whisper` transcribe, ese texto entra al mismo router de v0.

- `io/input_voice.py`
- `faster-whisper` `large-v3`, `int8_float16`, CUDA
- Buffer de audio en RAM, descartado tras transcribir

Deliberadamente **sin wake word**. Push-to-talk evita VAD, ruido ambiente y falsos
positivos, que son un proyecto entero aparte.

**Terminado cuando:**
- [ ] STT < 400 ms en frases de ~3 s
- [ ] `ollama ps` y `nvidia-smi` confirman que nada swapea
- [ ] Ningún archivo de audio queda en disco tras una sesión

**Rama:** `feature/stt-push-to-talk`

---

## v3 — Vive en el sistema

- `pystray` — ícono de bandeja
- `pynput` — hotkey global para el push-to-talk
- Task Scheduler al iniciar sesión

A partir de acá es una herramienta de uso diario, no un script que se corre a mano.
Esta es la versión que revela si el proyecto sirve: **si a las tres semanas no lo estás
usando a diario, el problema es la latencia o el catálogo de skills, no la falta de wake
word.** Resolver eso antes de seguir.

Incluye el **watchdog de audio**: health-check cada 30 s sobre la varianza de las
muestras, reapertura del stream, latido en el audit log. Sin esto el asistente muere en
silencio la primera vez que desconectás los audífonos.

**Terminado cuando:**
- [ ] Sobrevive a un reinicio de Windows
- [ ] Sobrevive a suspender y reanudar el equipo
- [ ] Sobrevive a desconectar el dispositivo de audio en caliente
- [ ] No pide permisos de administrador en ningún momento
- [ ] Uso diario real durante una semana

**Rama:** `feature/system-integration`

---

## Spike — Wake word en español (antes de la v4)

**Un fin de semana. El código se tira después.** Es la pieza menos predecible del
proyecto y hay que des-arriesgarla temprano.

- Montar el pipeline de entrenamiento de `openWakeWord` en Docker sobre WSL2 + CUDA
- Entrenar el nombre candidato
- Medir falsos positivos en una hora de uso normal y con la TV encendida

Si el nombre elegido tiene mala tasa de detección en español, se elige otro nombre. Mejor
saberlo ahora que en el mes cuatro.

---

## v4 — Wake word

- `openWakeWord`, modelo entrenado en el spike
- `silero-vad` para detectar el fin del habla
- **Estados de residencia**: dormido → despertando (warm-up especulativo) → activo →
  enfriando
- Skill `cambiar_nombre`: reentrena el modelo y reemplaza el `.onnx`

**Terminado cuando:**
- [ ] < 1 falso positivo por hora en uso normal
- [ ] Wake word → inicio de captura en < 100 ms
- [ ] En reposo: 0 VRAM, < 100 MB de RAM, < 5 % de un núcleo
- [ ] El primer comando tras días de reposo cumple el presupuesto de latencia normal
- [ ] El micrófono se puede desactivar desde la bandeja
- [ ] `cambiar_nombre` funciona de punta a punta sin intervención manual

**Rama:** `feature/wake-word`

---

## v5 — El LLM como router

Reemplaza el fallback del matcher. Las skills ya tienen descripción y JSON Schema, así
que casi no se toca código.

- Ollama, `qwen3:8b`, `keep_alive: -1`, thinking mode desactivado
- Tool definitions en formato OpenAI, descripciones en inglés
- Regla de contenido no confiable → modo solo-lectura

**Terminado cuando:**
- [ ] Golden set completo (50–100 frases): ≥ 95 % skill, ≥ 90 % params
- [ ] Latencia p95 del camino LLM < 700 ms
- [ ] El matcher de frases sigue resolviendo el camino común sin invocar al LLM
- [ ] Los tests de inyección de prompt pasan: el asistente cae a solo-lectura
- [ ] Un tool call inválido produce "no entendí", nunca una acción improvisada

**Rama:** `feature/llm-router`

---

## v6 — Automatizaciones

Aquí vive la idea original de "que haga cosas solo". Pero esto no son comandos: son
**triggers**. Es un subsistema distinto con su propio ciclo de vida.

- Cron / scheduler interno
- Watchers de archivos
- Eventos del sistema

**Advertencia de diseño:** un trigger es una skill que se ejecuta sin que nadie la haya
pedido. La compuerta de ejecución sigue aplicando, pero ya no hay un humano para
confirmar. Ninguna skill destructiva puede ser disparada por un trigger. Sin excepciones.

**Rama:** `feature/automation-triggers`

---

## Fuera de alcance (por ahora)

Cosas que van a sonar tentadoras y hay que rechazar hasta que la v3 esté en uso diario:

- Interfaz web / dashboard
- Sincronización entre dispositivos
- Modelos más grandes "para que entienda mejor"
- Cualquier skill que necesite privilegios de administrador
- Streaming de audio hacia servicios externos
