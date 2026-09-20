# IDUCDEV — Asistente de Búsqueda de Empleo y Clientes

Asistente personal para delegar todo el proceso tedioso de buscar
**empleo** (vacantes Flutter/Dart remotas, freelance y mercado oculto) y
**clientes** (leads de negocio y empresas target), con deduplicación
central para que **nunca se repita** nada.

> **Agentes de IA:** lee [AGENTS.md](AGENTS.md) antes de tocar el repo.

## 📘 Guía de uso

- **→ [GUIA.md](GUIA.md)** — manual del usuario: frases para delegar, qué
  hace por ti, dónde se guarda cada cosa y cómo restaurarlo.
- **→ [docs/SKILLS.md](docs/SKILLS.md)** — detalle técnico de las skills.

## 🧠 El cerebro (`estado/`)

| Archivo | Qué es |
|---------|--------|
| `config.py` | Fuente única de rutas (`.iducdev-root`, nunca hardcodear) |
| `historial.json` | Base central "no repitas esto" (dedup) |
| `tareas.json` | Bandeja de entrada (acciones + vencimientos) |
| `rondas.json` | Bitácora de rondas (fases + conteos) |
| `tracker.py` | Helper del historial (consulta/registro/estado) |
| `orquestador.py` | CLI: `ronda`, `registrar`, `estado`, `marcar`, `tareas`, `informe` |

## 📁 Estructura

```
├── GUIA.md                      # Guía del usuario (leer primero)
├── AGENTS.md                    # Guía para agentes de IA
├── docs/
│   └── SKILLS.md                # Detalle técnico de las skills
├── README.md                    # Este archivo
├── isaac-urdaneta-base.md       # CV base (nunca se modifica)
├── cv-ats-prompt.md             # Reglas ATS para CVs
├── CV_*.md / *.pdf              # CVs y PDFs generados
├── .opencode/
│   ├── skills/                  # Las 8 skills (proyecto-only)
│   └── command/                 # /ronda /estado /nuevo
├── vacantes/                    # Vacantes del día
├── vacantes-workana/            # Proyectos freelance
├── vacantes-ocultas/            # Vacantes de posts de LinkedIn
├── clientes-potenciales/        # Leads de negocio (scoring)
├── empresas-target/             # Empresas para aplicar
├── mensajes-outreach/           # Mensajes de contacto
├── informes/                    # Resumen diario de la ronda
└── estado/                      # El cerebro (ver tabla arriba)
```

## 🚀 Empezar

Abre opencode en esta carpeta y di:

```
"Haz la ronda de hoy"
```

El asistente busca empleos y clientes nuevos, omite lo ya visto y te
deja un resumen en `informes/`. Ver la [guía](GUIA.md) para más frases.

Comandos rápidos de opencode:
- `/ronda` → ejecuta la ronda del día
- `/estado` → qué hay nuevo / pendiente
- `/nuevo` → registrar manualmente un item en el historial

## 🔒 Dependencias

- `python3`, `pandoc`, `fonts-liberation` (para generar PDFs)
- Navegador Chrome (para LinkedIn, empresas y leads)
- Skills de proyecto en `.opencode/skills/` (el repo es su respaldo)