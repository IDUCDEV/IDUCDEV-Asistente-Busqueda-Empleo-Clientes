# IDUCDEV — Asistente de Búsqueda de Empleo y Clientes

Asistente personal para delegar todo el proceso tedioso de buscar
**empleo** (vacantes Flutter/Dart remotas, freelance y mercado oculto) y
**clientes** (leads de negocio y empresas target), con deduplicación
central para que **nunca se repita** nada.

## 📘 Guía de uso

**→ [GUIA.md](GUIA.md)** — cómo usarlo: frases para delegar, qué hace por
ti, dónde se guarda cada cosa y cómo restaurarlo.

## 📁 Estructura

```
├── GUIA.md                      # Guía sencilla (leer primero)
├── GUIA-Skills.md               # Detalle técnico de las skills
├── README.md                    # Este archivo
├── isaac-urdaneta-base.md       # CV base (nunca se modifica)
├── cv-ats-prompt.md             # Reglas ATS para CVs
├── CV_*.md / *.pdf              # CVs y PDFs generados
├── vacantes/                    # Vacantes del día
├── vacantes-workana/            # Proyectos freelance
├── vacantes-ocultas/            # Vacantes de posts de LinkedIn
├── clientes-potenciales/        # Leads de negocio (scoring)
├── empresas-target/             # Empresas para aplicar
├── mensajes-outreach/           # Mensajes de contacto
├── informes/                    # Resumen diario de la ronda
├── estado/
│   ├── historial.json           # Base central "no repitas esto"
│   └── tracker.py               # Helper de deduplicación
└── skills-backup/               # Respaldos de skills para restaurar
```

## 🚀 Empezar

Abre opencode en esta carpeta y di:

```
"Haz la ronda de hoy"
```

El asistente busca empleos y clientes nuevos, omite lo ya visto y te
deja un resumen en `informes/`. Ver la [guía](GUIA.md) para más frases.

## 🔒 Dependencias

- `python3`, `pandoc`, `fonts-liberation` (para generar PDFs)
- Navegador Chrome (para LinkedIn, empresas y leads)
- Skills en `~/.opencode/skills/` (respaldadas en `skills-backup/`)