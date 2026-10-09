---
name: flutter-employers
description:Descubre empresas LATAM y globales remote-first con vacantes Flutter/Dart reales, sondeando sus tableros de empleo (Greenhouse/Ashby/Lever/Workday) vía empresas_search.py. El script resuelve ats+slug desde la página de carreras, filtra roles Flutter, descarta los no alcanzables desde LATAM y los registra en estado/empresas_registry.json + resultados/empresas-target/{fecha}-empresas-vacantes.md. Complementa al descubrimiento manual con web search (ver hidden-jobs-web).
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
| `estado/verificar_registro.py` | alta de empresas con tablero **verificado** |
| `estado/empresas_seed.json` | semilla de candidatos (editable; no es el registro) |
| `estado/empresas_registry.json` | registro persistente (versionado) |
| `estado/empresas_cache.json` | cache de sondeo (TTL 24 h) |
| `resultados/empresas-target/{fecha}-empresas-vacantes.md` | salida del día |
| `resultados/empresas-target/leads-db.json` | histórico (se migra al registro) |

---

## Tableros soportados

| ATS | Endpoint | Notas |
|---|---|---|
| Greenhouse | `GET boards-api.greenhouse.io/v1/boards/{slug}/jobs` | JSON público |
| Ashby | `GET api.ashbyhq.com/posting-api/job-board/{slug}` | JSON público |
| Lever | `GET api.lever.co/v0/postings/{slug}?mode=json` | JSON público |
| **Workday** | `POST {host}/wday/cxs/{tenant}/{site}/jobs` | JSON público, **POST** |

> **Workday sí tiene API pública.** La premisa de que no la tenía era falsa, y
> por eso antes se marcaba `revisar_navegador`. Es el endpoint CXS, el mismo
> `EmploymentSite` público que consulta el navegador, sin credenciales:
>
> ```
> POST https://<host>/wday/cxs/<tenant>/<site>/jobs
> {"appliedFacets":{},"limit":20,"offset":0,"searchText":"flutter"}
> ```
>
> Dos trampas, ambas medidas contra tableros reales:
> 1. El `<site>` del path CXS **no lleva el locale**: `wday/cxs/rappi/es/Rappi_jobs`
>    responde **405**; `wday/cxs/rappi/Rappi_jobs` responde **200**. El locale sí va
>    en la URL de navegación (la del informe).
> 2. El `<tenant>` **no** es la primera etiqueta del host: en `nvidia.wd5.…` es
>    `nvidia`, en `rappi.wd12.…` es `rappi` (el `wd<N>` es el subdominio, no el
>    tenant). Se prueban los candidatos en orden hasta que uno responde.
>
> `searchText` busca en título **y** descripción (NVIDIA: `"GeForce"` → 47,
> `"Pune"` → 93), así que un solo POST con `"flutter"` ya es señal fiable de que
> no hay vacantes Flutter. Workday devuelve fechas relativas (`"Posted 13 Days
> Ago"`) y no trae descripción en el listado (vive en un endpoint por vacante),
> por eso el rol normalizado lleva el flag `matched`.

El registro codifica Workday como `ats="workday:<host>"` y `slug="<locale>/<site>"`.

---

## FASE 1 + 2 — Automáticas (script)

```bash
python3 .opencode/skills/flutter-employers/empresas_search.py --limit 60
python3 .opencode/skills/flutter-employers/empresas_search.py --company belvo --verbose
python3 .opencode/skills/flutter-employers/empresas_search.py --refresh     # ignora cache
python3 .opencode/skills/flutter-employers/empresas_search.py --stats       # resumen
python3 .opencode/skills/flutter-employers/empresas_search.py --min-score 45
python3 .opencode/skills/flutter-employers/empresas_search.py --dry-run     # no escribe nada
```

Qué hace el script, en orden:

1. **Resuelve el tablero**, en tres pasos:
   - `ats`/`slug` ya guardados en el registro (camino corto, 0 peticiones extra);
   - **`resolve_board`**: deduce `(proveedor, slug)` leyendo las páginas de
     carrera de la empresa (`/careers`, `/jobs`, `/vacantes`, `/empleo`,
     `/trabalhe-conosco`). **Es el paso que rinde.**
   - slugs candidatos a ciegas — **desactivados por defecto**
     (`--slugs-ciegos` para activarlos). Medido: ~0 % de acierto en LATAM
     (25 empresas → 0 tableros) y cuestan ~10 peticiones por empresa, o sea la
     ronda entera.
   - Tope **10 intentos por empresa**, con presupuesto que se **reinicia en cada
     empresa**. Ojo: era un contador global, así que en una ronda de 60 empresas
     solo se sondeaban ~6 (la primera agotaba el presupuesto de todas).
2. **Filtra stack.** Flutter/Dart en el título → entra; móvil con Flutter solo
   en la descripción → entra marcado `review`; en Workday, `matched` (el tablero
   confirmó Flutter/Dart en el cuerpo aunque el título no lo diga) → entra. Un
   `matched` de `mobile` **no** cuenta: no es Flutter.
3. **Filtra aplicabilidad** (`es_aplicable`). Un puesto presencial en India,
   Japón, Alemania o EE. UU. no se puede aceptar desde Venezuela: se descarta.
   Solo se descarta lo inequívoco (país explícito no LATAM **y** sin señal de
   remoto). Si el tablero no dice nada, no se descarta.
4. **Puntúa** 0-100: Flutter en título 40 · Flutter en descripción 15 · remoto 20 ·
   LATAM-friendly 15 · seniority compatible 10 · fecha publicada 5.
   `--min-score N` descarta lo que quede por debajo.
5. **Deduplica** contra la categoría `vacantes_empresa` del historial central
   (clave canónica `empresa::titulo`, ver `tracker.canon_vacancy_key`).
6. **Sale**: `---JOBCOUNT---/---SKIPPED---/---SOURCES---/---ERRORS---` (mismo
   protocolo que consume `orquestador.py`), más el markdown del día.

### Estados del registro

| status | Significa |
|---|---|
| `nuevo` | nunca sondeada |
| `con_vacante` | tiene roles Flutter/Dart abiertos |
| `sin_vacante_flutter` | su tablero tiene vacantes, pero ninguna de Flutter |
| `tablero_vacio` | el tablero respondió con 0 vacantes (slug probablemente equivocado) |
| `sin_tablero` | no se pudo localizar un tablero |
| `revisar_navegador` | *legacy*: era Workday; ya no se usa (ahora se parsea) |

> **No concluyas "no hay vacantes"** con `tablero_vacio`: casi siempre es slug
> equivocado. Suele pasar con `greenhouse/nubank` (existe pero Nubank usa otro).

## FASE 3 — Ampliar el registro

### Vía automática: `verificar_registro.py`

```bash
python3 estado/verificar_registro.py --stats      # qué falta
python3 estado/verificar_registro.py --dry-run    # prueba la semilla, no escribe
python3 estado/verificar_registro.py              # registra lo verificado
python3 estado/verificar_registro.py --limit 20 --verbose
```

Funciona al revés de lo habitual: **no** se inventan empresas y slugs esperando
que acierten. Se parte de `estado/empresas_seed.json` (candidatos con nombre +
dominio), el script **prueba el tablero de cada uno** y solo da de alta los que
devuelven ≥1 vacante real, guardando `ats` + `slug` + la `careers_url` que lo
reveló, para que las próximas rondas vayan por el camino corto. El "verified on
entry" es empírico, no declarativo.

- Corre en paralelo (`EMPRESAS_WORKERS`, 8 hilos) con un `Prober` por hilo: los
  contadores son por empresa y compartirlos entre hilos los corrompería.
- Es **idempotente**: una empresa ya registrada solo se refresca.
- También re-sondea las empresas del registro cuyo tablero no está resuelto, lo
  que **repara placeholders antiguos** (había entradas con `ats: "workday"` y
  `slug: "wd12"`, del tiempo en que Workday "no tenía API").
- Imprime progreso en vivo (`[38/154] ✓ Rappi → workday:…`).

### Tablero vacío: depende de dónde salió el slug

Un tablero que responde con 0 vacantes significa dos cosas distintas, y el
script lo distingue con `Prober.resolution`:

| `resolution` | Significado | ¿Se registra? |
|---|---|---|
| `careers` | el slug lo dedujo la página de la propia empresa | **Sí.** El slug es fiable: 0 vacantes ES "no hay vacantes" |
| `registro` | ya estaba guardado | sí, si trae vacantes |
| `ciego` | el slug se adivinó | **No.** Vacío casi siempre es slug equivocado |

Para ampliar la lista de la semilla, edita `estado/empresas_seed.json`.

### Vía manual: descubrimiento con web search

Los slugs a ciegas casi nunca aciertan en LATAM, así que para lo que el script no
cubre:

1. `hidden-jobs-web` (skill hermana): `site:boards.greenhouse.io flutter`,
   `site:jobs.ashbyhq.com flutter`, `site:jobs.lever.co flutter` — descubre
   empresas **y** su slug en una sola pasada.
2. Crunchbase / YC / listas públicas de startups LATAM.

Al añadir una empresa al registro a mano, respetar el orden de prioridad:

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
- La lectura de páginas de carreras usa un timeout corto
  (`EMPRESAS_CAREERS_TIMEOUT_S`, 3 s) y **corta en el primer `__NET__`**: si el
  dominio no resuelve, las otras 4 rutas tampoco van a resolver. Medido, esto
  bajó la corrida de la semilla de ~50 min a ~17.
- Un host que no resuelve (`__NET__`) **no** cuenta como fallo ni dispara el
  cortocircuito: es un subdominio retirado, no "el sitio nos bloquea". Distinguir
  `__NET__` de `__ERR__` evita que un tenant muerto de Workday pare la ronda.
- El script nunca borra entradas del registro.
- `leads-db.json` es un dict **por fecha**; `migrate_leads_db()` lo aplana al
  arrancar con el registro vacío. No volver a leerlo a mano.
- Tests: `estado/tests/test_empresas_search.py`.