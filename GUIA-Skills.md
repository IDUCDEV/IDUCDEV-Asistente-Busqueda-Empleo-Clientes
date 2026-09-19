# Guía de Skills para Búsqueda de Empleo y Clientes

**Léeme primero: [GUIA.md](GUIA.md)** — guía sencilla para el usuario final.
Este documento es el detalle técnico de las skills instaladas.

## Skills disponibles

| # | Skill | Propósito | Tipo | Invocación |
|---|-------|-----------|------|------------|
| 0 | **asistente-empleo-clientes** | Orquestador central. Punto único de entrada para buscar empleo + clientes, con dedup central | AI guiada | Cargar la skill → delegar cualquier petición |
| 1 | **job-search** | Busca vacantes Flutter/Dart en 7 fuentes (LinkedIn, GetOnBoard, Himalayas, RemoteJobs, Career Nest, Jobicy, Computrabajo) | Script Python | `python3 $OPENCODE_SKILLS/job-search/job_search.py` |
| 2 | **workana-search** | Busca proyectos freelance en Workana (Mobile Development), marca Flutter/Dart ✅ | Script Python | `python3 $OPENCODE_SKILLS/workana-search/workana_search.py` |
| 3 | **linkedin-hidden-jobs** | "Hidden job market": posts de LinkedIn con vacantes, no avisos oficiales | AI guiada + navegador | Cargar la skill → ejecuta el workflow |
| 4 | **cv-apply** | CV optimizado ATS + carta + PDF a partir de una descripción de vacante | AI guiada | Cargar la skill → pegar descripción |
| 5 | **linkedin-outreach** | Mensaje personalizado para contactar reclutadores en LinkedIn | AI guiada | Cargar la skill → pegar URL de perfil |
| 6 | **flutter-employers** | Descubre empresas target (startups + establecidas) en LATAM y globales remote-first que usan Flutter | AI guiada (pipeline 4 fases) | Cargar la skill → ejecuta el pipeline |
| 7 | **prospectar-clientes** | Genera leads de negocios venezolanos que necesiten web/apps/n8n | AI guiada (pipeline 4 fases) | Cargar la skill → ejecuta el pipeline |

---

## 0. asistente-empleo-clientes — Orquestador (ENTRADA ÚNICA)

Es la puerta de entrada a todo. Absorbe peticiones como *"haz la ronda de
hoy"*, *"solo empleos"*, *"solo clientes"*, *"aplica a X"*, *"contacta a Y"*
y decide qué sub-skills ejecutar. **Garantiza que nada se repita** usando
`estado/historial.json`.

**Archivos:** `~/.opencode/skills/asistente-empleo-clientes/SKILL.md`

### Fases de la "ronda diaria"

```
1. job-search            → vacantes/            (script)
2. workana-search        → vacantes-workana/    (script)
3. linkedin-hidden-jobs  → vacantes-ocultas/    (navegador)
4. prospectar-clientes   → clientes-potenciales/(navegador)
5. flutter-employers     → empresas-target/     (navegador)
   ─────────────────────────────────────────────────────
   consolidar            → informes/{fecha}-resumen.md
```

---

## Deduplicación central (NO REPETIR NADA)

Todas las skills consultan y actualizan la misma base:

```
estado/historial.json   ← "memoria" del asistente
estado/tracker.py       ← helper (Historial, normalize_*, vacancy_key)
```

| Categoría | Clave |
|-----------|-------|
| `vacantes` | `empresa_normalizada::titulo_normalizado` |
| `empresas` | dominio o nombre normalizado |
| `clientes` | dominio o nombre del negocio |
| `proyectos_workana` | slug del proyecto |
| `posts_linkedin` | URL del post |
| `outreach` | URL del perfil |

Ver estado:
```bash
python3 "estado/tracker.py" stats
```

`job_search.py` y `workana_search.py` ya deduplican solos contra el
historial e imprimen `---SKIPPED---` (cantidad omitida). Las skills
guiadas por IA deben consultar/actualizar el historial al iniciar/terminar.

---

## 1. job-search — Buscador de vacantes

```bash
python3 ~/.opencode/skills/job-search/job_search.py
```

- 7 fuentes con paginación (LinkedIn, GetOnBoard, Himalayas, RemoteJobs,
  Career Nest, Jobicy, Computrabajo).
- Filtra Flutter/Dart, remoto, LATAM (LinkedIn ≤24h).
- Normaliza salarios a USD/mes.
- Dedup entre sesiones contra `estado/historial.json`.
- Output: `vacantes/{YYYY-MM-DD}.md`

## 2. workana-search — Proyectos freelance

```bash
python3 ~/.opencode/skills/workana-search/workana_search.py
```

- Scrapea Workana (IT & Programming > Mobile Development, hasta 20 págs).
- Marca con ✅ proyectos Flutter/Dart.
- Dedup entre sesiones (por slug) contra `estado/historial.json`.
- Output: `vacantes-workana/{YYYY-MM-DD}.md`

## 3. linkedin-hidden-jobs — Mercado laboral oculto

- Navega LinkedIn Search (sesión del usuario) con queries mixtas
  es/EN para posts que publican vacantes (no avisos).
- Filtros: URL `linkedin.com/posts`, oferta real, remoto/LATAM, últimos 3 días.
- Registra posts vistos en `estado/historial.json`.
- Output: `vacantes-ocultas/{YYYY-MM-DD}-hidden.md`

## 4. cv-apply — CV optimizado ATS

- Análisis de vacante → decisión con pesos (Flutter core 40%, match ≥ 60%).
- Genera CV optimizado + carta + PDF (`pandoc`, Liberation Sans).
- Archivos base: `isaac-urdaneta-base.md`, `cv-ats-prompt.md`.
- Al aplicar, actualizar estado de la vacante a `applied` en el historial.

## 5. linkedin-outreach — Mensajes para LinkedIn

- Lee CV base → busca info del perfil → pregunta tono → genera mensaje.
- Registra el perfil contactado en `estado/historial.json`.
- Output: `mensajes-outreach/{nombre}-{YYYY-MM-DD}.md`

## 6. flutter-employers — Discovery de empresas target

- FASE 1: websearch + GitHub + LinkedIn + directorios (máx 12 queries).
- FASE 2: dedup normalizado contra `empresas-target/leads-db.json`.
- FASE 3: enriquecer top 5-8 (website + careers + LinkedIn).
- FASE 4: scoring 0-100 (Hot/Warm/Cold) → output + DB.
- Output: `empresas-target/{YYYY-MM-DD}-empresas.md`, `leads-db.json`

## 7. prospectar-clientes — Prospección de leads (VE)

- FASE 1: Overpass API (OpenStreetMap) + infoguia + websearch.
- FASE 2: visitar y analizar websites con Imagen/IA.
- FASE 3: scoring con IA (`service_match`, `pain_points`, `icebreaker`).
- FASE 4: output + DB.
- Output: `clientes-potenciales/{YYYY-MM-DD}-leads.md`, `leads-db.json`

---

## Flujo recomendado

```
Diario:  "Haz la ronda de hoy"  → orquestador: empleos + clientes
Semanal: flutter-employers + prospectar-clientes (descubrir más)
A demanda: cv-apply (aplicar) · linkedin-outreach (contactar)
```

Siempre delegar vía el orquestador (`asistente-empleo-clientes`) para
que la deduplicación central funcione.

---

## Respaldo y restauración

Las skills están respaldadas en `skills-backup/` (incluye el orquestador).

```bash
# Restaurar después de formatear
git clone <repo> "~/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes"
cp -r skills-backup/* ~/.opencode/skills/
ls ~/.opencode/skills/
```

Dependencias externas: `pandoc`, `fonts-liberation`, `python3`, Chrome.

---

## Preguntas frecuentes

- **"Busqué dos veces el mismo día y no vi la vacante."** → Si ya estaba
  en `estado/historial.json`, se omite a propósito (así no se repite).
  El resumen te dice cuántas omitió.
- **"Quiero ver todo otra vez."** → Pide explícitamente "muéstrame todo,
  ignora el historial" y el asistente consultará las fuentes sin filtrar.
- **"¿Dónde está mi historial?"** → `estado/historial.json`