# IDUCDEV — Asistente de Búsqueda de Empleo y Clientes

Asistente personal para delegar todo el proceso tedioso de buscar
**empleo** (vacantes Flutter/Dart remotas, freelance y mercado oculto) y
**clientes** (leads de negocio y empresas target), con deduplicación
central para que **nunca se repita** nada.

> **📘 Guía completa del proyecto:** **→ [GUIA.md](GUIA.md)**. Es el único
> documento que necesitas: uso, centro de recursos, dónde caen los
> resultados, comandos y restauración.
>
> **Agentes de IA:** lee [AGENTS.md](AGENTS.md) y consulta
> [`recursos/INDICE.md`](recursos/INDICE.md) antes de tocar el repo.

## Estructura en dos zonas

| Zona | Qué es |
|------|--------|
| `recursos/` | **Centro de recursos**: lo que el asistente consulta (tu CV base, reglas ATS, guías). Los mantienes tú. Ver [GUIA.md §3](GUIA.md). |
| `resultados/` | **Resultados por skill**: dónde cada skill plasma su salida (vacantes, leads, CVs, mensajes, informes). Ver [GUIA.md §4](GUIA.md). |

## 🧠 El cerebro (`estado/`)

| Archivo | Qué es |
|---------|--------|
| `config.py` | Fuente única de rutas (`.iducdev-root`, nunca hardcodear) |
| `historial.json` | Base central "no repitas esto" (dedup) |
| `tareas.json` | Bandeja de entrada (acciones + vencimientos) |
| `rondas.json` | Bitácora de rondas (fases + conteos) |
| `tracker.py` | Helper del historial (consulta/registro/estado) |
| `orquestador.py` | CLI: `ronda`, `registrar`, `estado`, `marcar`, `tareas`, `informe` |

## 🚀 Empezar

Abre opencode en esta carpeta y di:

```
"Haz la ronda de hoy"
```

El asistente busca empleos y clientes nuevos, omite lo ya visto y te deja
un resumen en `resultados/informes/`. Ver [GUIA.md](GUIA.md) para más frases.

Comandos rápidos de opencode:
- `/ronda` → ejecuta la ronda del día
- `/estado` → qué hay nuevo / pendiente
- `/nuevo` → registrar manualmente un item en el historial

## 🔒 Dependencias

- `python3`, `pandoc`, `fonts-liberation` (para generar PDFs)
- Navegador Chrome (para LinkedIn, empresas y leads)
- Skills de proyecto en `.opencode/skills/` (el repo es su respaldo)