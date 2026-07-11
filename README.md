# Asistente virtual local

Asistente de voz local para Windows: entiende órdenes, ejecuta acciones acotadas sobre la
máquina y **responde hablando**. Privado (nada sale del equipo), reversible y construido
por fases.

> **Versión actual: v1 — el asistente habla.**
> Escribís por teclado, te responde con voz. El micrófono llega en la v2.

---

## 1. Qué hace esta versión

**Funciona:**

- **REPL de texto**: escribís una orden, la ejecuta y te contesta **con voz** (Piper, local).
- **4 skills**:
  - `hora` — te dice la hora. *("qué hora es")*
  - `abrir_app` — abre una app del whitelist. *("abre spotify")*
  - `nota` — anota texto en un archivo, dentro de la jaula de rutas. *("tomá nota comprar pan")*
  - `clima` — placeholder; declara permiso de red pero aún no está implementada.
- **Seguridad activa**: compuerta de ejecución, permisos declarativos por skill, jaula de
  rutas (rechaza `..`, UNC, ADS y symlinks que escapan) y log de auditoría en JSONL.
- **Capa de persona**: normaliza el texto antes de hablarlo (puntuación, espacios) y aplica
  el perfil de `config/persona.yaml`.
- **Degradación elegante**: si falta el modelo de voz, sigue funcionando en modo texto.

**Todavía no:**

- No escucha (sin micrófono). → v2
- No tiene wake word ni corre en segundo plano. → v3 y v4
- El router usa coincidencia de frases, no un LLM. Órdenes fuera del catálogo no las
  entiende. → v5

---

## 2. Puesta en marcha (desde cero, en cualquier máquina)

**Requisitos:** Windows 10/11 y **Python 3.11 de python.org** (no el de MSYS2 ni el de la
Microsoft Store; sus librerías nativas dan problemas más adelante).

```bash
# 0. Instalar Python 3.11 si no está
winget install Python.Python.3.11
# (cerrá y reabrí la terminal después de instalar)

# 1. Entorno virtual aislado
py -3.11 -m venv .venv
.venv\Scripts\activate
# El prompt debe mostrar (.venv) al inicio. Si no lo ves, no sigas.

# 2. Dependencias
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. Descargar una voz en español (~60 MB, no se versiona)
python -m piper.download_voices es_MX-ald-medium --download-dir voices

# 4. Verificar que todo está sano
python -m pytest -q
# Esperado: 24 passed, 1 skipped
# (el test de symlink se salta en Windows: crearlos exige permisos de admin)

# 5. Arrancar
python main.py
# Debe imprimir: [voz activa: Piper]
```

**Cada vez que abrás una terminal nueva**, activá el entorno antes de trabajar:
`.venv\Scripts\activate`

### Probarlo

En el REPL, escribí:

```
qué hora es          → te responde con voz
abre spotify         → pedirá que agregues la app a apps.yaml
tomá nota comprar pan → pedirá que configures la carpeta de notas
salir
```

### Habilitar las skills que necesitan configuración

- **`abrir_app`** → en `config/apps.yaml`, mapeá nombre a ruta del ejecutable:
  ```yaml
  spotify: C:\Users\TU_USUARIO\AppData\Roaming\Spotify\Spotify.exe
  ```
- **`nota`** → en `config/permisos.yaml`, declará la carpeta permitida:
  ```yaml
  nota: ["C:\\Users\\TU_USUARIO\\Documents\\notas"]
  ```

### Ajustar la voz

En `config/persona.yaml`, bajo `voz`:

- `length_scale` — `1.2` habla más lento, `0.9` más rápido.
- `modelo` — otra voz de [piper-samples](https://rhasspy.github.io/piper-samples)
  (descargala con el comando del paso 3 y apuntá la ruta acá).

---

## 3. Idea del proyecto

La voz es un **adaptador de entrada/salida**. El proyecto real es el **registro de skills**
+ el **router de intenciones** + la **compuerta de seguridad**. Todo lo demás se enchufa
alrededor de ese núcleo sin tocarlo.

```
core/            # el núcleo estable (no cambia entre versiones)
  skill.py         # contrato base de Skill + Permisos + Resultado
  registry.py      # descubre y registra skills automáticamente
  router.py        # texto → Intencion (v1: matcher; v5: + LLM)
  gate.py          # compuerta: valida, confirma, ejecuta, audita
  sandbox.py       # jaula de rutas
  audit.py         # log append-only en JSONL
  contexto.py      # últimos N turnos + flags de confianza
  config.py        # carga de los YAML
  persona.py       # capa de estilo pre-voz
skills/          # acciones concretas (agregar una NO toca core/)
adapters/        # capa de entrada/salida intercambiable
  input_cli.py / output_console.py   # activos
  output_tts.py / tts_piper.py       # activos (voz con Piper)
  input_voice.py                     # stub (v2)
config/          # apps.yaml, permisos.yaml, persona.yaml, .env.example
tests/           # golden set del router, jaula, persona
docs/            # ARCHITECTURE.md y ROADMAP.md (el plano completo)
main.py          # punto de entrada
```

### Principios

- **Núcleo + adaptadores.** El núcleo no sabe si el input vino del teclado o del micrófono.
- **Seguridad desde el día uno.** La compuerta, los permisos y el audit log no son una fase
  posterior: retrofitear seguridad no ocurre nunca.
- **El router nunca emite comandos**, solo intenciones estructuradas. Whitelist, jamás
  blacklist.
- **Nada se borra** (papelera, no borrado) y **nunca corre como administrador**.
- **Por fases**, y cada fase es usable por sí sola.

### Agregar una skill

Copiá el patrón de `skills/hora.py`: subclase de `Skill`, definí `nombre`, `descripcion`
(en inglés, para el LLM de la v5), `frases`, `permisos`, e implementá `ejecutar()`. El
registry la descubre sola. Son ~15 líneas y no se toca `core/`.

---

## 4. Problemas comunes

| Síntoma | Causa | Solución |
|---|---|---|
| `No module named pytest` / `piper` | El venv no está activo, o faltan dependencias | `.venv\Scripts\activate` y `pip install -r requirements.txt` |
| `[voz desactivada: configurá 'voz.modelo'...]` | Falta el modelo de voz | Correr el paso 3 (descargar la voz) |
| `ModuleNotFoundError: No module named 'core'` | Se ejecutó desde otra carpeta | Correr `python main.py` **desde la raíz** del repo |
| Errores raros de permisos o archivos | El proyecto está dentro de OneDrive y sincroniza el `.venv` | Pausar OneDrive para esa carpeta, o mover el proyecto fuera |

---

## 5. Hoja de ruta

`v0` núcleo · `v0.5` jaula de archivos · **`v1` voz de salida ← estás acá** · `v2` micrófono ·
`v3` bandeja y autostart · `v4` wake word · `v5` router con LLM · `v6` automatizaciones

Detalle completo en `docs/ROADMAP.md`. Arquitectura, modelo de seguridad y decisiones
técnicas en `docs/ARCHITECTURE.md`.

## Licencia y créditos

Voz: [Piper](https://github.com/OHF-Voice/piper1-gpl) (GPL-3.0), local y offline.
