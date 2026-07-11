# Asistente virtual local

Asistente de voz local para Windows: escucha, entiende, ejecuta acciones acotadas sobre
la máquina y responde hablando. Privado (nada sale del equipo), reversible y construido
por fases.

> **Estado actual: v0 — esqueleto funcional.** REPL de texto, sin micrófono ni voz. El
> núcleo (registry, router, compuerta, auditoría) está vivo y con tests en verde. Las
> capas de voz son adaptadores que se enchufan en versiones posteriores.

## Idea en una frase

La voz es un adaptador de entrada. El proyecto real es el **registro de skills** + el
**router de intenciones** + la **compuerta de seguridad**. Todo lo demás se enchufa
alrededor de ese núcleo sin tocarlo.

## Cómo correrlo

Desde la raíz del repo:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
python main.py          # abre el REPL
python -m pytest -q     # corre los tests
```

En el REPL, probá: `qué hora es`, `abre spotify`, `cómo está el clima`, `salir`.

Para que `abre <app>` funcione, agregá la ruta del ejecutable en `config/apps.yaml`.

## Estructura

```
core/            # el núcleo estable (no cambia entre versiones)
  skill.py         # contrato base de Skill + Permisos + Resultado
  registry.py      # descubre y registra skills automáticamente
  router.py        # texto → Intencion (v0: matcher; v5: + LLM)
  gate.py          # compuerta: valida, confirma, ejecuta, audita
  sandbox.py       # jaula de rutas (base; se endurece en v0.5)
  audit.py         # log append-only en JSONL
  contexto.py      # últimos N turnos + flags de confianza
  persona.py       # capa de estilo pre-voz (v0: passthrough)
skills/          # acciones concretas (agregar una NO toca core/)
  hora.py          # funcional
  abrir_app.py     # funcional (lee config/apps.yaml)
  clima.py         # placeholder (declara red=True)
adapters/        # capa "io": entrada/salida intercambiable
  input_cli.py / output_console.py   # v0
  input_voice.py / output_tts.py     # stubs (v2 / v1)
config/          # apps.yaml, permisos.yaml, persona.yaml, .env.example
tests/           # golden set del router + tests de la jaula
docs/            # ARCHITECTURE.md y ROADMAP.md (el plano completo)
main.py          # punto de entrada (REPL)
```

## Principios

- **Núcleo + adaptadores.** El núcleo no sabe si el input vino del teclado o del
  micrófono. Por eso el sistema completo se construye antes de tocar audio.
- **Seguridad desde la v0.** La compuerta, los permisos declarativos y el audit log no
  son una fase posterior. Retrofitear seguridad no ocurre nunca.
- **El router nunca emite comandos**, solo intenciones estructuradas. Whitelist, jamás
  blacklist.
- **Nada se borra** (papelera, no borrado) y **nunca corre como administrador**.
- **Por fases**, y cada fase es usable por sí sola. Ver `docs/ROADMAP.md`.

## Agregar una skill

Copiá el patrón de `skills/hora.py`: subclase de `Skill`, definí `nombre`, `descripcion`
(en inglés, para el LLM), `frases`, `permisos`, e implementá `ejecutar()`. El registry la
descubre sola. Son ~15 líneas y no se toca `core/`.

## Documentación

- `docs/ARCHITECTURE.md` — arquitectura completa, modelo de seguridad, presupuestos de
  latencia y VRAM, decisiones (ADR).
- `docs/ROADMAP.md` — las versiones v0 → v6 con sus criterios de "terminado".
