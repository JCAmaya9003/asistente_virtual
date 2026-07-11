# Arquitectura

Asistente virtual local para Windows. Escucha, entiende, ejecuta acciones acotadas
sobre la máquina y responde hablando.

---

## 1. Propósito y no-objetivos

**Propósito.** Ejecutar un conjunto pequeño y auditable de acciones locales a partir de
lenguaje natural, en español, con latencia baja y sin que los datos del usuario salgan
de la máquina.

**No-objetivos** (explícitos, para poder rechazar propuestas más adelante):

- No es un chatbot de propósito general. Si la respuesta es "conversar", el proyecto falló.
- No ejecuta código arbitrario ni comandos de shell. Nunca.
- No corre con privilegios de administrador. Si una acción necesita elevación, esa acción no existe.
- No expone puertos de red.
- No borra archivos.

---

## 2. Requisitos no funcionales

Estos requisitos tienen poder de veto sobre cualquier decisión de diseño posterior.

### 2.1 Presupuesto de latencia

De que el usuario termina de hablar a que empieza a salir audio de respuesta.

| Etapa | Objetivo | Motor |
|---|---|---|
| Wake word → inicio de captura | < 100 ms | openWakeWord |
| STT | < 400 ms | faster-whisper, CUDA |
| Router — camino rápido | < 5 ms | matcher de frases |
| Router — camino LLM | < 700 ms (TTFT) | Ollama, qwen3:8b |
| TTS, primer chunk de audio | < 300 ms | Piper, streaming |
| **Total percibido — camino rápido** | **< 900 ms** | |
| Total percibido — camino LLM | < 1.6 s | |

Si el total pasa de ~1.5 s de forma consistente, el asistente se siente muerto y se deja
de usar. Esta tabla es el criterio de aceptación de cada versión, no una aspiración.

### 2.2 Presupuesto de VRAM

Los tres modelos compiten por la misma tarjeta. Verificar con `ollama ps` que
`size_vram` sea igual al tamaño del modelo; si es menor, hay swapping y la latencia se
va a 5–15 s.

| Componente | VRAM aprox. |
|---|---|
| faster-whisper `large-v3` (int8_float16) | ~2.5 GB |
| Ollama `qwen3:8b` (Q4_K_M) | ~5.5 GB |
| Piper | CPU, 0 GB |

El router es una tarea fácil (elegir entre ~15 opciones). No gastar VRAM ahí: subir de
8B a 14B mejora poco y compite con Whisper, que sí se beneficia del modelo grande.

### 2.3 Privacidad y reversibilidad

- El audio vive en RAM y se descarta tras transcribir. Nunca toca el disco.
- Ninguna acción es irreversible. Lo que "se borra" va a la papelera (`send2trash`).
- Toda ejecución queda registrada en un log append-only.

### 2.4 Residencia: el estado por defecto es dormido

El asistente corre 24/7 pero pasa el 99 % del tiempo sin tocar la GPU.

| Estado | Qué está cargado | RAM | VRAM | CPU |
|---|---|---|---|---|
| Dormido | Solo el wake word (ONNX ~200 KB) | ~80 MB | 0 | 2–3 % de un núcleo |
| Despertando | Cargando Whisper + Ollama en paralelo | — | subiendo | pico |
| Activo | Whisper + LLM residentes | ~200 MB | ~8 GB | variable |
| Enfriando | Todo residente, timer de 5 min corriendo | ~200 MB | ~8 GB | ~0 |

**El warm-up especulativo.** El usuario tarda 1–3 s en decir el comando. Esa es la
ventana de carga, y es gratis. Al disparar el wake word se lanzan en paralelo, antes de
saber qué va a decir:

1. La carga de `faster-whisper` a la GPU.
2. Una petición dummy a Ollama para residenciar el modelo.

Cuando el usuario termina de hablar, todo está caliente. El cold start no desaparece:
se esconde detrás de la propia voz del usuario.

**Enfriado.** `keep_alive: 5m` en Ollama y un timer propio que libera Whisper. Si hay un
segundo comando dentro de la ventana, no se nota. Si no, vuelve a dormido.

**Refinamiento opcional (STT de dos niveles).** Para que el camino común nunca toque la
GPU: un `faster-whisper base` int8 en CPU, siempre residente (~150 MB, ~500 ms, ~90 % de
precisión). El matcher compara contra un conjunto cerrado de frases, así que tolera el
error de transcripción. Solo si el matcher no acierta con confianza alta se carga
`large-v3` en GPU y se re-transcribe.

### 2.5 El watchdog

Lo que mata a un asistente always-on no es el consumo, es que muere en silencio.

| Falla | Síntoma | Detección |
|---|---|---|
| Cambia el dispositivo de audio | El stream entrega ceros, sin excepción | Health-check cada 30 s: varianza de las muestras ≠ 0 |
| Suspensión / reanudación de Windows | Stream muerto | Mismo health-check |
| Crash del proceso | Nada | Task Scheduler relanza; latido en el audit log |

Un latido cada N minutos en el log JSONL. Si el último latido es de hace tres días, se
sabe exactamente qué pasó.

**Nota de UX.** Con el stream abierto, Windows 11 muestra el ícono de micrófono en la
bandeja permanentemente. No se puede evitar. Se convierte en feature: un toggle en el
ícono de bandeja que suspende la escucha, para que el usuario vea cuándo el asistente
oye y cuándo no.

---

## 3. Vista general

El sistema se divide en un **núcleo** estable y **adaptadores** intercambiables.

```
  Entrada                    Núcleo                      Salida
  ───────                    ──────                      ──────
  CLI          ┌──────────────────────────────┐      Consola
  Voz  ──────► │  Router  ──►  Compuerta  ──► │ ───► TTS
               │                  │           │
               │              Registro        │
               │              de skills       │
               └──────────────────────────────┘
                              │
                         Audit log
```

La entrada y la salida son detalles de implementación. El núcleo no sabe si el texto
vino de un teclado o de un micrófono, ni si la respuesta se imprime o se habla. Esto es
lo que permite construir el sistema completo antes de tocar el micrófono.

---

## 4. El contrato de Skill

Una skill es una unidad de acción autocontenida. El criterio de calidad del diseño es:
**agregar una skill nueva cuesta ~15 líneas y no toca nada de `core/`.** Si hay que
editar el router para agregar una skill, el diseño está mal.

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Permisos:
    lee_archivos: bool = False
    escribe_archivos: bool = False
    red: bool = False
    destructiva: bool = False
    raices_permitidas: tuple[str, ...] = ()   # jaula: rutas absolutas

class Skill:
    nombre: str                 # "abrir_app"
    descripcion: str            # EN INGLÉS. Se la damos al LLM como tool description.
    esquema: dict               # JSON Schema de los parámetros
    frases: tuple[str, ...]     # patrones para el matcher rápido
    permisos: Permisos

    def ejecutar(self, params: dict, ctx: Contexto) -> Resultado:
        ...
```

**Por qué la descripción va en inglés.** Los modelos se entrenaron con schemas de
function calling mayoritariamente en inglés. Las descripciones traducidas degradan la
precisión de selección de herramienta, aunque la conversación con el usuario sea en
español. El texto que ve el usuario y el texto que ve el modelo son cosas distintas.

**El manifiesto de permisos es declarativo y el núcleo niega por defecto.** Una skill
sin `red: True` no puede abrir un socket, sin importar lo que diga su código.

---

## 5. El router

El router traduce texto a una intención estructurada. Nunca produce comandos.

```python
@dataclass
class Intencion:
    skill: str          # nombre registrado, validado contra el registry
    params: dict        # validado contra el JSON Schema de la skill
    origen: str         # "keywords" | "llm"
    confianza: float
```

### 5.1 Estrategia híbrida

1. **Matcher de frases.** Resuelve el ~80% de las órdenes reales, que son las mismas
   quince frases. Determinista, ~5 ms, cero alucinación.
2. **LLM como fallback.** Solo si el matcher no encuentra nada. Ollama local con
   `qwen3:8b`, tool calling en formato OpenAI, thinking mode desactivado (agrega
   latencia y no aporta con 15 herramientas).
3. **Fallo cerrado.** Si el LLM no devuelve un tool call válido, el asistente dice que
   no entendió. No improvisa.

### 5.2 Configuración de Ollama

- `keep_alive: 5m` — ver la sección 2.4. **No usar `-1`**: reserva la VRAM para siempre.
- Warm-up especulativo: al disparar el wake word, se emite una petición dummy a Ollama
  para que suba el modelo mientras el usuario todavía está hablando.
- Verificar soporte con `ollama show qwen3:8b` (`tools` debe aparecer en Capabilities).
- Estructurar la salida con JSON Schema, no confiar en el parseo de texto libre.
- Ollama atiende una petición a la vez. No es un problema con un solo usuario, pero es
  un techo conocido.

### 5.3 Criterio de aceptación

Un **golden set** de 50–100 frases en español con `(skill, params)` esperados. Métricas:

- Exactitud de skill: ≥ 95 %
- Exactitud de parámetros: ≥ 90 %
- Latencia p95 del camino LLM: < 700 ms

Si el modelo no llega, se cambia el modelo — no se cambia el criterio.

---

## 6. Modelo de seguridad

### 6.1 Amenazas

| # | Amenaza | Probabilidad | Impacto |
|---|---|---|---|
| A1 | El asistente se equivoca y actúa sobre lo que no debe | Alta | Medio |
| A2 | Inyección de prompt vía contenido leído (archivo, web, correo) | Media | Alto |
| A3 | Exposición externa: puertos, secretos, audio saliente | Baja | Alto |

### 6.2 La trifecta letal

Tres capacidades que, **juntas en un mismo turno**, convierten al asistente en un
exfiltrador de datos:

1. Acceso a datos privados.
2. Exposición a contenido no confiable.
3. Capacidad de comunicarse hacia afuera.

Cualquiera de las tres por separado es inofensiva. El diseño debe hacer imposible que
coexistan, no confiar en que no coincidan.

**Regla operativa:** en el momento en que una skill lee contenido no confiable, el
contexto entra en modo solo-lectura por el resto del turno. Las skills con `red: True`
o `escribe_archivos: True` quedan bloqueadas.

```python
if ctx.leyo_contenido_no_confiable:
    if skill.permisos.red or skill.permisos.escribe_archivos:
        raise Rechazo("modo solo-lectura: se leyó contenido no confiable")
```

### 6.3 La compuerta de ejecución

Nada la esquiva.

```
Intención ──► Validación ──► Confirmación ──► Ejecución
              (tipos,        (solo si es      (en jaula,
               permisos)      destructiva)     con log)
                  │
                  └──► Rechazo (queda en el log)
```

**Validación.** El nombre de skill existe en el registry. Los params validan contra el
JSON Schema. Los permisos requeridos están declarados en el manifiesto. Whitelist, nunca
blacklist de comandos peligrosos.

**Jaula de rutas.** Toda skill que toca archivos recibe `raices_permitidas`. Se resuelve
el path real y se rechaza cualquier cosa fuera. En Windows, cuidado con:

- `..` y symlinks (`os.path.realpath` antes de comparar)
- rutas UNC (`\\servidor\recurso`)
- insensibilidad a mayúsculas (normalizar con `os.path.normcase`)
- Alternate Data Streams (`archivo.txt:oculto`)

**Confirmación.** Solo para operaciones destructivas, y el conjunto de operaciones
destructivas debe ser diminuto. La confirmación se pide por el canal del usuario, nunca
la genera el LLM. Ojo con la fatiga de confirmación: si preguntás por todo, el usuario
dice que sí por reflejo y la defensa vale cero.

**Nada se borra.** `send2trash` a la papelera de Windows. La reversibilidad vale más que
cualquier confirmación.

### 6.4 Controles transversales

- El proceso corre como usuario normal. Sin UAC, sin elevación.
- Sin puertos abiertos. Si algún día hay HTTP, `127.0.0.1` + token.
- Secretos en `.env`, fuera del control de versiones. Una skill solo ve las claves que
  su manifiesto declara.
- Modo `--dry-run` obligatorio en toda skill destructiva.

---

## 7. Voz

### 7.1 Salida (TTS)

El motor vive detrás de una interfaz. La decisión de motor no bloquea nada.

```python
class TTSEngine(Protocol):
    def hablar(self, texto: str) -> Iterator[bytes]: ...   # streaming
```

**Motor por defecto:** Piper, voz neutral en español, CPU, casi tiempo real.

**Por qué no clonar la voz de un personaje.** La voz de un personaje es la voz de un
actor: una persona real e identificable. Clonarla implica entrenar sobre material con
copyright para imitar a alguien. Fuera de discusión para un repositorio público de
portafolio.

**Alternativa recomendada si se quiere timbre propio:** grabar diez minutos de la propia
voz y entrenar Piper o XTTS. Es legal, es tuyo, y como demo es más impresionante.

**Nota de latencia:** XTTS y RVC en CPU tardan segundos por frase y rompen el
presupuesto de la sección 2.1. Piper no.

### 7.2 La capa de persona

El timbre no es lo que hace que suene a un personaje. El texto sí. Antes de mandar al
TTS, la respuesta pasa por `core/persona.py`, que reescribe el fraseo según un perfil
configurable (vocabulario, muletillas, ritmo, longitud). Esta capa es donde vive el
carácter del asistente, y es 100 % independiente del motor de voz.

### 7.3 Entrada (STT)

- `faster-whisper`, modelo `large-v3`, `compute_type="int8_float16"`, `device="cuda"`.
- Con CUDA disponible, `large-v3` supera ampliamente a `small` en español y sigue
  dentro del presupuesto de latencia.
- El buffer de audio vive en RAM y se descarta tras transcribir.
- **Sesgo de nombres propios.** Whisper destroza los nombres de marca ("espotifai").
  Pasarle `initial_prompt` con las claves de `apps.yaml` sube la precisión sobre esos
  tokens. Además, el matcher hace fuzzy match contra un conjunto cerrado, así que
  tolera error residual.

### 7.4 Wake word

`openWakeWord`. El nombre del asistente es configurable, pero cambiarlo significa
**entrenar un modelo nuevo**, no editar un YAML.

El pipeline genera miles de pronunciaciones sintéticas del nombre con Piper TTS variando
voz, velocidad y tono, las aumenta con ruido y respuestas de impulso de sala, y entrena
un clasificador pequeño. La salida es un ONNX de ~200 KB que corre en CPU en tiempo real.

**Restricciones conocidas:**

- El entrenamiento automatizado solo corre en Linux (dependencias de Piper). En Windows:
  WSL2 con CUDA.
- Entorno de dependencias frágil (PyTorch 1.13.1, TensorFlow 2.8.1, Python 3.10 clavado).
  Encapsular en Docker una sola vez.
- ~4 GB de datos de entrenamiento compartidos, descarga única.
- El frontend (melspectrograma + embedding) fue entrenado con voz en inglés. Funciona en
  español, pero el umbral de detección hay que tunearlo empíricamente. **Prototipar esto
  antes de comprometerse con la v4.**

**`cambiar_nombre` es una skill.** Invoca el contenedor de entrenamiento y reemplaza el
`.onnx`. El asistente se rebautiza a sí mismo. Cuesta minutos de GPU, lo cual está bien:
nadie cambia el nombre tres veces al día.

**Alternativa descartada:** Silero VAD + Whisper `tiny` con fuzzy match sobre el nombre.
Es el único camino con nombre verdaderamente instantáneo, pero transcribe todo lo que se
habla cerca y la latencia de detección es ~10× peor.

---

## 8. Entrada y control en Windows

| Necesidad | Solución | Nota |
|---|---|---|
| Abrir apps | `os.startfile()` / `subprocess.Popen` | Ruta desde `apps.yaml` |
| Descubrir apps | Escanear `.lnk` del menú de inicio | Propone candidatos; el usuario aprueba |
| Push-to-talk | `pynput` | No usar la librería `keyboard`: a veces exige elevación |
| Bandeja del sistema | `pystray` | |
| Autostart | Task Scheduler, al iniciar sesión | Mejor que la carpeta Startup: reinicia si crashea |
| Captura de audio | `sounddevice` | |

El descubrimiento de apps es deliberado: el asistente **pide permiso para conocer una
app**. Escanea `%APPDATA%\Microsoft\Windows\Start Menu\Programs`, muestra los candidatos
y el usuario los aprueba hacia `apps.yaml`. Coherente con el modelo de seguridad.

---

## 9. Estructura del repositorio

```
asistente/
  core/
    skill.py         # clase base + Permisos
    registry.py      # descubre y registra skills
    router.py        # texto -> Intencion (híbrido)
    gate.py          # compuerta de ejecución
    sandbox.py       # jaula de rutas
    audit.py         # log append-only
    persona.py       # capa de estilo pre-TTS
    contexto.py      # últimos N turnos + flags de confianza
  skills/
    hora.py
    abrir_app.py
    clima.py
  adapters/         # capa "io"; renombrada para no chocar con el módulo io de Python
    input_cli.py
    input_voice.py
    output_console.py
    output_tts.py
  config/
    apps.yaml        # nombre -> ruta ejecutable
    permisos.yaml    # raíces permitidas por skill
    persona.yaml     # perfil de estilo
    .env             # API keys (gitignored)
  tests/
    test_golden_set.py
    test_sandbox.py
  main.py
docs/
  ARCHITECTURE.md
  ROADMAP.md
```

---

## 10. Contexto conversacional

"Abrí Spotify" seguido de "subile el volumen" requiere que el segundo turno sepa de qué
habla el primero. `core/contexto.py` guarda los últimos N turnos (N = 5 es suficiente) y
un par de flags:

```python
@dataclass
class Contexto:
    turnos: deque[Turno]
    leyo_contenido_no_confiable: bool = False
    ultima_skill: str | None = None
```

Es poco código y es la diferencia entre un asistente y un ejecutor de comandos.

---

## 11. Observabilidad

Log append-only en JSONL desde el primer commit. Es la auditoría de seguridad y también
la mejor herramienta de debug del proyecto.

```json
{"ts":"2026-07-08T14:03:11Z","skill":"abrir_app","params":{"nombre":"spotify"},
 "origen":"keywords","resultado":"ok","ms":42}
{"ts":"2026-07-08T14:03:40Z","skill":"borrar_temp","params":{"ruta":"C:\\Windows"},
 "origen":"llm","resultado":"rechazo","motivo":"fuera de jaula","ms":3}
```

---

## 12. Estrategia de pruebas

- **Golden set** (`tests/test_golden_set.py`): 50–100 frases → `(skill, params)`
  esperados. Mide exactitud y latencia. Es el criterio de aceptación del router.
- **Jaula** (`tests/test_sandbox.py`): casos maliciosos de rutas — `..`, UNC, symlinks,
  mayúsculas, ADS. Debe rechazar todos.
- **Sin micrófono.** Ninguna prueba del núcleo toca hardware de audio. Si hay que hablar
  para probar el router, la arquitectura está acoplada.
- **Inyección de prompt**: archivos de prueba con instrucciones embebidas. El asistente
  debe caer a solo-lectura y no ejecutar nada.

---

## 13. Decisiones de arquitectura

| # | Decisión | Alternativa descartada | Razón |
|---|---|---|---|
| 1 | Voz neutral en español, motor intercambiable | Clonar voz de personaje | Derechos del actor y copyright; el repo es público |
| 2 | Router híbrido (frases + LLM) | LLM para todo | Latencia y determinismo en el camino común |
| 3 | LLM local con Ollama | API en la nube | El asistente lee archivos locales: privacidad |
| 4 | `qwen3:8b` | `qwen3:14b` | Elegir entre 15 skills es fácil; la VRAM va a Whisper |
| 5 | Papelera, no borrado | Diálogo de confirmación | Reversibilidad > confirmación; la confirmación se automatiza mentalmente |
| 6 | Push-to-talk antes que wake word | Wake word primero | Desacopla el riesgo: VAD y falsos positivos son un proyecto aparte |
| 7 | Seguridad en la v0 | Seguridad como fase posterior | Retrofitear permisos a un sistema que ya funciona no ocurre nunca |
| 8 | Descripciones de tools en inglés | Todo en español | Los schemas de function calling se entrenaron en inglés |
| 9 | `keep_alive: 5m` + warm-up especulativo | `keep_alive: -1` | Reservar 5.5 GB de VRAM 24/7 hace la máquina inusable para otra cosa |
| 10 | Wake word entrenado por nombre | VAD + Whisper tiny siempre escuchando | Latencia, falsos positivos y transcripción constante del ambiente |
| 11 | Watchdog de audio desde la v3 | Confiar en que el stream sobreviva | Los asistentes always-on mueren en silencio, no por consumo |
