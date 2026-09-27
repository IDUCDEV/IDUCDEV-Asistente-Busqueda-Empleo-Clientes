---
name: job-search
description: Úsala cuando el usuario pida buscar vacantes Flutter/Dart remotas (LATAM o US). Consulta 12 fuentes (LinkedIn ≤24h y ≤7d, GetOnBoard, Himalayas, RemoteJobs, Career Nest, Jobicy, Computrabajo, Remotico, Workremoto, Wellfound, elempleo.co), filtra, deduplica contra el historial central y genera el listado markdown. Para mobile.career/YC/X o para buscar empresas por tablero, ver hidden-jobs-web y flutter-employers.
---

# Skill: job-search

Buscador de vacantes Flutter para LATAM. Cuando el usuario invoque esta skill, ejecuta:

```bash
python3 .opencode/skills/job-search/job_search.py
```

Esto orquesta TODO el workflow (fetch, parse, filtros, dedup, markdown).  
El script imprime la ruta del archivo generado (en `resultados/vacantes/{fecha}.md`),
conteos y errores.  
Muéstrale el resultado al usuario e indica que puede aplicar con `cv-apply`.

Si invocas la skill dentro de la ronda, ejecútala vía orquestador:
```bash
python3 estado/orquestador.py ronda --empleos
```

---

## Fuentes

### 1. LinkedIn (HTML, guest API, ≤24h)

**URL:**
```
https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Flutter&f_WT=2&f_TPR=r86400&location=Latin%20America&start=0
```

**Formato:** `html`
**Filtro de fecha:** `f_TPR=r86400` ya filtra ≤24h desde LinkedIn
**Filtro de modalidad:** `f_WT=2` (remoto)
**Ubicación:** Latin America

**Queries (3, para subir precisión):**
1. `keywords=Flutter`
2. `keywords="Flutter Developer"` (frase exacta)
3. `keywords=Dart`

**Nota importante (matching difuso de LinkedIn):** desde 2026 la guest API devuelve
roles cuyo título NO contiene "Flutter/Dart" (ej. "Mobile Engineer", "Desenvolvedor
Mobile") y requiere el keyword de búsqueda. Por eso el parser:
- Mantiene el rol si el título contiene Flutter/Dart → `✅ Confirmado`.
- Lo mantiene marcado **`⚠ verificar`** si es un rol mobile/software sin Flutter/Dart
  en el título (revisar el aviso antes de aplicar).
- Descarta ruido claro (`delphi`, `cto`, `socio`, `lowcode`, `analytics`, `react`,
  `on-site`, `designer`, `devops`, entre otros; ver regex `LI_NOISE` en el script).

**Extraer por cada job card:**
- Título del puesto (dentro de `.base-search-card__title` o `h3`)
- Nombre de empresa (dentro de `.base-search-card__subtitle` o `h4`)
- Ubicación (dentro de `.job-search-card__location`)
- Link directo (href del `a.base-card__full-link` o similar)
- Tiempo de publicación (texto como "hours ago", "1 day ago")

---

### 2. GetOnBoard (API JSON pública)

**URL:**
```
https://www.getonbrd.com/api/v0/search/jobs?query=flutter&remote=true&per_page=20
```

**Formato:** `text` (devuelve JSON)
**Nota:** Sin autenticación. LATAM nativo.

**Extraer:**
- `data[].title`
- `data[].company.name` o `data[].company` (el campo exacto depende de la respuesta)
- `data[].url` o `permalink`
- `data[].published_at` o `published_date`
- `data[].salary` si existe
- `data[].country` o `data[].location`
- `data[].modality` (remote)
- `data[].seniority`

**Filtrar:**
- Si `remote` no viene en `true`, verificar que la ubicación sea LATAM y el tipo remoto
- Ordenar por fecha de publicación descendente

---

### 3. Himalayas (API JSON pública)

**URL:**
```
https://himalayas.app/jobs/api/search?q=flutter&sort=recent
```

**Formato:** `text`
**Nota:** API pública sin auth. Remoto worldwide.

**Extraer:**
- `title`
- `company.name`
- `url`
- `salaryMin`, `salaryMax`, `currency`
- `seniority`
- `pubDate` (ISO 8601)
- `locationRestrictions[]` (array de países donde aplica)
- `categories[]`
- `employmentType`
- `parentCategories[]`

**Filtrar:**
- Mantener solo si `categories` o `parentCategories` incluye "Engineering" o "Mobile"
- `locationRestrictions` vacío o incluye países LATAM (o es worldwide)

---

### 4. RemoteJobs.org (API JSON pública)

**URL:**
```
https://remotejobs.org/api/v1/jobs?q=flutter&category=programming&limit=50
```

**Formato:** `text`
**Nota:** API pública sin auth. 800+ jobs.

**Extraer:**
- `data[].title`
- `data[].company.name`
- `data[].url`
- `data[].location`
- `data[].salary_min`, `data[].salary_max`
- `data[].posted_at`
- `data[].type`

---

### 5. Career Nest (API JSON pública — inestable)

**URL:**
```
https://careernest.cloud/api/feed?category=software-development&type=remote&limit=50
```

**Formato:** `text`
**Nota:** El dominio a veces no responde. El script lo maneja como fallback silencioso.

**Extraer:**
- `jobs[].title`
- `jobs[].company`
- `jobs[].location`
- `jobs[].job_type`
- `jobs[].salary.min`, `jobs[].salary.max`, `jobs[].salary.currency`
- `jobs[].posted_at`
- `jobs[].job_url`

---

### 6. Jobicy (API JSON pública)

**URL:**
```
https://jobicy.com/api/v2/remote-jobs?count=50&tag=flutter
```

**Formato:** `text`
**Nota:** API pública sin auth. Remoto worldwide.

**Extraer:**
- `jobs[].id`
- `jobs[].jobTitle`
- `jobs[].companyName`
- `jobs[].url`
- `jobs[].jobGeo` (geographic restriction)
- `jobs[].jobLevel`
- `jobs[].jobIndustry`
- `jobs[].salaryMin`, `jobs[].salaryMax`

---

### 7. Computrabajo (HTML scraping, país por país)

**URLs (una por país):**
```
https://ve.computrabajo.com/trabajo-de-flutter   (Venezuela)
https://mx.computrabajo.com/trabajo-de-flutter   (México)
https://co.computrabajo.com/trabajo-de-flutter   (Colombia)
https://ar.computrabajo.com/trabajo-de-flutter   (Argentina)
https://cl.computrabajo.com/trabajo-de-flutter   (Chile)
https://pe.computrabajo.com/trabajo-de-flutter   (Perú)
https://ec.computrabajo.com/trabajo-de-flutter   (Ecuador)
```

**Formato:** `html` (o `markdown` según lo que funcione mejor)
**Nota:** HTML server-renderizado, sin JS necesario.

**Extraer por cada oferta laboral:**
- Título del puesto
- Nombre de la empresa
- Ubicación (ciudad, estado/país)
- Salario (si aparece)
- Tipo de trabajo: Presencial / Remoto / Híbrido (buscar indicadores en el texto)
- Fecha de publicación (texto como "Hace X horas/días")
- Link a la oferta

**Filtrar por país:**
- **Venezuela (ve):** TODAS las modalidades (remoto ✅, híbrido ✅, presencial ✅)
- **Resto de países (mx, co, ar, cl, pe, ec):** Solo remoto. Si no se puede determinar la modalidad, incluir pero marcar como "⚠ revisar"

---

### 8. Remotico.io (HTML SSR + JSON-LD)

**URLs:**
```
https://remotico.io/jobs/skill/flutter
https://remotico.io/jobs/skill/dart
```

**Formato:** `html` (Nuxt con SSR; sin JS necesario)
**Nota:** Remoto worldwide con fuerte presencia LATAM y BR/pt-BR.

**Tarjeta (para extraer):**
- Título: `<span class="relative">TÍTULO</span>` dentro del `h3` del `<a href="/jobs/<slug>">`
- Empresa: `<p class="text-xs ... truncate">EMPRESA</p>`
- Tiempo: texto "hace X días" (span `shrink-0`)

**Enriquecimiento (`enrich_remotico`):** fetchea la página del empleo
`https://remotico.io/jobs/<slug>` (tope 12) y lee el bloque `application/ld+json`
tipo `JobPosting`: `hiringOrganization.name`, `datePosted`, 
`applicantLocationRequirements[]` (países donde aplica), `baseSalary` (si existe).

**Filtrar:** el endpoint `skill/flutter|dart` ya viene acotado por tag; mantener
todo lo que liste la página.

---

### 9. Workremoto.com (RSS WordPress)

**URL:**
```
https://workremoto.com/categoria-empleo/desarrollo/feed/
```

**Formato:** `text` (RSS XML)
**Nota:** Empleos 100% remotos en español (AR, CL, CO, MX y otros LATAM). El feed
de IT (`/categoria-empleo/it/feed/`) existe pero hoy está vacío; se mantiene solo
`desarrollo`.

**Extraer por cada `<item>`:**
- `<title>` (quitar el sufijo "– Remoto")
- `<link>` (URL del empleo `/empleos/<slug>`)
- `<pubDate>` → "hace X días/h"
- `<description>` (texto plano; detecta Flutter/Dart y empresa con el patrón
  "«Empresa» busca...")

**Filtrar:** `has_flutter_dart(title, description)`.

---

### 10. LinkedIn ≤7 días (segunda pasada)
Misma `parse_linkedin`, pero `f_TPR=r604800` (7 días) en vez de `r86400` (24 h).
4 queries × 4 páginas. Se etiqueta `LinkedIn (7d)` para que el informe separe lo
fresco de lo tibio.

**Por qué existe:** con solo 24 h se descartaban vacantes LATAM de 2-7 días, que
siguen abiertas. Es la fuente #1 de vacantes LATAM del usuario.

### 11. Wellfound (HTML SSR)
`wellfound.com/role/flutter-developer?page=N` (3 págs) y
`wellfound.com/location/south-america?role=flutter-developer` (2 págs).
Puesto en `/jobs/{id}-{slug}`, empresa en `/company/{slug}` + `<h2>`.
Salario en formato `$140K–$180K`; seniority en el título.

> **Requiere el User-Agent completo** (`Chrome/... Safari/537.36`). Con el UA
> truncado responde 403. Es la fuente nueva más productive (~20 roles/página).

### 12. elempleo.com (Colombia)
`elempleo.com/co/ofertas-empleo/trabajo-desarrollador-flutter`. Cada tarjeta lleva
sus datos en el atributo `data-ga4-offerdata` (JSON con `&quot;` escapado):
`title`, `company`, `location`, `salary`, `tags`. Modalidad en
`div.js-work-modality`.

> La búsqueda **no pagina** (`totalPages=1`) y devuelve ~20 items de los que solo
> ~3-4 son Flutter. El filtro de relevancia es obligatorio; el resto es ruido
> (cobol, rpa, cnc). Colombia → solo remoto, se descartan híbrido/presencial.

---

## Filtros globales (aplicar DESPUÉS de parsear cada fuente)

| Filtro | Regla |
|--------|-------|
| **Tecnología** | Título debe contener "Flutter" o "Dart" (case-insensitive). Si no hay título claro, mantener si la descripción lo menciona. |
| **LinkedIn** | ≤24 h en la 1ª pasada; ≤7 días en la 2ª (etiqueta aparte) |
| **elempleo.com** | Título con Flutter/Dart, o móvil con Flutter en la descripción (`review`). El resto se descarta |
| **Venezuela (Computrabajo VE)** | Incluir remoto + híbrido + presencial |
| **Resto de fuentes/países** | Solo remoto |
| **Duplicados** | Misma empresa + mismo título → fusionar, mostrar una vez (priorizar la fuente con más datos) |
| **Antigüedad** | LinkedIn: ≤24 h. Otras fuentes: ordenar por más reciente |

---

## Notas de mantenimiento

- **User-Agent:** mantenerlo completo. Varias fuentes dan 403 si lo recortas.
- **Paginación:** `fetch_source(name, url, fmt, parser, pages, step, start)`. El
  `step`/`start` es por fuente (LinkedIn/Himalayas: offsets de 10/20; Wellfound:
  `?page=1..N`). No hardcodear `p * 10`.
- **Rutas:** `OUTPUT_DIR` sale de `config.OUTPUT_DIRS["vacantes"]`, no de una
  ruta escrita a mano.
- **Prueba sin ensuciar el historial:** `--dry-run` no escribe el `.md` ni
  `historial.json`.
- Para lo que no es parseable por HTTP (mobile.career, YC, X, `site:boards.*`),
  usar la skill hermana `hidden-jobs-web`.

---

## Output: formato del markdown

```markdown
# Vacantes Flutter - {fecha}

> 🎯 Buscador automático · {hora} UTC · {n} fuentes consultadas
> 📍 Remoto LATAM {si aplica "(+ Venezuela presencial/híbrido)"}

---

## LinkedIn ({n} vacantes · ≤24h)

### {ID}. {Título}
**Empresa:** {empresa}
**Ubicación:** {ubicación} | **Modalidad:** {remoto/híbrido/presencial}
**⏰** {tiempo} | **💰** {salario si aplica}
**🔗** [{fuente}]({url})
`[Aplicar con cv-apply]`

---

## GetOnBoard ({n} vacantes)

### {ID}. {Título}
...

(se repite el mismo bloque para Himalayas, RemoteJobs.org, Jobicy, Career Nest,
 Computrabajo por país, Remotico y Workremoto)

## LinkedIn 7d ({n} vacantes · ≤7 días)

### {ID}. {Título}
**Empresa:** {empresa}
**Ubicación:** {ubicación} | **Modalidad:** {remoto}
**⏰** {tiempo}
**🔗** [{url}]({url})

## Wellfound ({n} vacantes)

### {ID}. {Título}
**Empresa:** {empresa}
**Ubicación:** {ubicación} | **Modalidad:** remoto
**💰** {salario} | **🎯** {seniority}
**🔗** [{url}]({url})

## elempleo.co ({n} vacantes · Colombia)

### {ID}. {Título}
**Empresa:** {empresa}
**Ubicación:** {ubicación} | **Modalidad:** remoto
**💰** {salario si aplica}
**🔗** [{url}]({url})
`⚠ verificar` (solo Flutter en la descripción)

> 📝 Para aplicar: copia el `🔗 link` y dímelo con "aplica a esta vacante" para generar CV personalizado con `cv-apply`.
```

---

## Salida en consola (protocolo del orquestador)

El script imprime, en este orden, para que `orquestador.py registrar` lo consuma:

```
---JOBCOUNT---
<n>
---SKIPPED---
<n>
---SOURCES---
<fuente>:<n>
...
---ERRORS---
<fuente>: <motivo>
```

Añadir fuentes nuevas exige mantener este contrato; `---SOURCES---` alimenta el
conteo por fase de `rondas.json`.

---

## Pipeline post-búsqueda

Cuando el usuario vea la lista y quiera aplicar a una:

1. Usuario dice: "aplica a esta" y pasa el link o descripción
2. Cargar la skill `cv-apply`
3. Ejecutar el workflow de `cv-apply`:
   - Leer CV base (`recursos/cv/base-isaac-urdaneta.md`)
   - Leer reglas ATS (`recursos/guias/cv-reglas-ats.md`)
   - Analizar la vacante
   - Generar CV optimizado en markdown
   - Generar carta de presentación
   - Convertir a PDF con pandoc
   - Mostrar resultado
4. Marcar la vacante como `applied`:
   ```bash
   python3 estado/orquestador.py marcar vacantes "<empresa::titulo>" applied
   ```

---

## Archivos de salida

```
resultados/vacantes/{YYYY-MM-DD}.md
```

Si se invoca varias veces el mismo día, sobrescribe el archivo del día (siempre la versión más reciente).