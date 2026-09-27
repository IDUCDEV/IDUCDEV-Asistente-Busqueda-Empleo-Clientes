---
name: flutter-employers
description:Descubre empresas LATAM y globales remote-first con vacantes Flutter/Dart reales, sondeando sus tableros de empleo (Greenhouse/Ashby/Lever) vía empresas_search.py. El script resuelve ats+slug desde la página de carreras, filtra roles Flutter y los registra en estado/empresas_registry.json + resultados/empresas-target/{fecha}-empresas-vacantes.md. Complementa al descubrimiento manual con web search (ver hidden-jobs-web).
---

# flutter-employers — Empresas Flutter con vacantes reales

## Principio

Los agregadores de empleo rendían 3-25 vacantes Flutter por corrida. Un tablero
de empresa expone el listado completo y sin intermediarios. Por eso la Fase 1 y 2
son **script determinista**, y el trabajo del agente es solo ampliar el registro.

## Archivos

| Ruta | Rol |
|---|---|
| `.opencode/skills/flutter-employers/empresas_search.py` | motor de sondeo |
| `estado/empresas_registry.json` | registro persistente (versionado) |
| `estado/empresas_cache.json` | cache de sondeo (TTL 24 h) |
| `resultados/empresas-target/{fecha}-empresas-vacantes.md` | salida del día |
| `resultados/empresas-target/leads-db.json` | histórico (se migra al registro) |

---

## FASE 1 + 2 — Automáticas (script)

```bash
python3 .opencode/skills/flutter-employers/empresas_search.py --limit 60
python3 .opencode/skills/flutter-employers/empresas_search.py --company belvo --verbose
python3 .opencode/skills/flutter-employers/empresas_search.py --refresh     # ignora cache
python3 .opencode/skills/flutter-employers/empresas_search.py --stats       # resumen
python3 .opencode/skills/flutter-employers/empresas_search.py --dry-run     # no escribe nada
```

Qué hace el script, en orden:

1. **Resuelve el tablero.** Primero usa `ats`/`slug` ya guardados; si no, deduce
   `(proveedor, slug)` leyendo la `careers_url` (`discover_ats`); si tampoco,
   prueba slugs candidatos a ciegas (`base`, prefijo de dominio, `+tech`,
   `+digital`, `+hiring`, `+careers`…). Tope 10 intentos por empresa.
2. **Filtra roles.** `has_flutter_dart(título)` → entra; móvil con Flutter solo
   en la descripción → entra marcado `review`; el resto se descarta.
3. **Puntúa** 0-100: Flutter en título 40 · Flutter en descripción 15 · remoto 20 ·
   LATAM-friendly 15 · seniority compatible 10 · fecha publicada 5.
4. **Deduplica** contra la categoría `vacantes_empresa` del historial central.
5. **Sale**: `---JOBCOUNT---/---SKIPPED---/---SOURCES---/---ERRORS---` (mismo
   protocolo que consume `orquestador.py`), más el markdown del día.

### Estados del registro

| status | Significa |
|---|---|
| `nuevo` | nunca sondeada |
| `con_vacante` | tiene roles Flutter/Dart abiertos |
| `sin_vacante_flutter` | su tablero tiene vacantes, pero ninguna de Flutter |
| `tablero_vacio` | el tablero respondió con 0 vacantes (slug probablemente equivocado) |
| `sin_tablero` | no se pudo localizar un tablero con los slugs probados |
| `revisar_navegador` | usa Workday u otro ATS sin API pública |

> **No concluyas "no hay vacantes"** con `tablero_vacio`: casi siempre es slug
> equivocado. Suele pasar con `greenhouse/nubank` (existe pero Nubank usa otro).

## FASE 3 — Ampliar el registro (agente)

Los slugs a ciegas casi nunca aciertan en LATAM: la vía fiable es conocer la
`careers_url` de cada empresa. Fuentes, en orden de rendimiento:

1. `hidden-jobs-web` (skill hermana): `site:boards.greenhouse.io flutter`,
   `site:jobs.ashbyhq.com flutter`, `site:jobs.lever.co flutter` — descubre
   empresas **y** su slug en una sola pasada.
2. `websearch` con `<empresa> careers` / `<empresa> jobs remote`. Nunca inventar
   la URL: verificarla (200) antes de guardarla.
3. Crunchbase / YC / listas públicas de startups LATAM.

Al añadir una empresa al registro, respetar el orden de prioridad:

```json
{"key": "slug","name": "Nombre","domain": "dominio.com","region": "latam|us|global",
 "tier": 1, "status": "nuevo", "added": "YYYY-MM-DD", "careers_url": "https://...",
 "last_checked": null, "open_roles": 0, "source": "..."}
```

**Prioridad: Tier 1 LATAM (que contratan LATAM) > Tier 2 US remote-first > Tier 3.**

## FASE 4 — Aplicar

Las vacantes detectadas se aplican con `cv-apply` (una a una). El seguimiento
(D+7) lo crea el historial al marcar `applied`:

```bash
python3 estado/orquestador.py marcar vacantes_empresa "<empresa>::<titulo>" applied
```

## Notas

- Respetar la pausa entre peticiones (`EMPRESAS_PAUSA_S`, 0.6 s). Son APIs
  públicas de terceros: no hacer ráfagas.
- El script nunca borra entradas del registro.
- `leads-db.json` es un dict **por fecha**; `migrate_leads_db()` lo aplana al
  arrancar con el registro vacío. No volver a leerlo a mano.
