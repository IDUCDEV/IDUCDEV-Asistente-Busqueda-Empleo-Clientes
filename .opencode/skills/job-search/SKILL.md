---
name: job-search
description: Use when the user asks to search for Flutter/remote/LATAM job vacancies. Queries 7 sources (LinkedIn, GetOnBoard, Himalayas, RemoteJobs, Career Nest, Jobicy, Computrabajo), filters, deduplicates, and generates a markdown listing.
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

## Filtros globales (aplicar DESPUÉS de parsear cada fuente)

| Filtro | Regla |
|--------|-------|
| **Tecnología** | Título debe contener "Flutter" o "Dart" (case-insensitive). Si no hay título claro, mantener si la descripción lo menciona. |
| **LinkedIn** | Solo ≤24h (ya viene filtrado, verificar en el texto de tiempo) |
| **Venezuela (Computrabajo VE)** | Incluir remoto + híbrido + presencial |
| **Resto de fuentes/países** | Solo remoto |
| **Duplicados** | Misma empresa + mismo título → fusionar, mostrar una vez (priorizar la fuente con más datos) |
| **Antigüedad** | LinkedIn: ≤24h. Otras fuentes: ordenar por más reciente |

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

(se repite el mismo bloque para Himalayas, RemoteJobs.org, Jobicy, Career Nest
 y Computrabajo por país)

> 📝 Para aplicar: copia el `🔗 link` y dímelo con "aplica a esta vacante" para generar CV personalizado con `cv-apply`.
```

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