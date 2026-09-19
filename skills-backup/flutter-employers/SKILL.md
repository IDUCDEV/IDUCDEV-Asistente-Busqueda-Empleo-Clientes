---
name: flutter-employers
description: Descubre empresas (startups + establecidas) en LATAM y globales remote-first que usan Flutter o podrían contratar un dev Flutter. Pipeline de 4 fases: descubrimiento (web search, GitHub, LinkedIn, directorios), enriquecimiento vía chrome-devtools, scoring, y output markdown + DB persistente. Sin outreach integrado — usa linkedin-outreach/cv-apply por separado.
---

# flutter-employers — Discovery de empresas target para Flutter dev

Busca empresas donde aplicar como desarrollador Flutter en LATAM y remoto 100%.
Enfocado en empresas **producto** (no agencias/consultoras): startups LATAM, empresas LATAM establecidas, y globales remote-first.

## Archivos de referencia

- **DB de empresas (historial):** `/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/empresas-target/leads-db.json`
- **Output del día:** `/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/empresas-target/{YYYY-MM-DD}-empresas.md`

---

## Resumen del pipeline

```
FASE 1: DESCUBRIMIENTO
  Web Search ────┐
  GitHub ────────┼──→ Lista única de empresas → cruzar con DB
  LinkedIn ──────┤
  Directorios ───┘

FASE 2: DEDUP + NORMALIZACIÓN
  Normalizar nombres → cotejar vs leads-db.json → solo nuevas

FASE 3: ENRIQUECIMIENTO (chrome-devtools)
  Top 5-8 empresas nuevas → visitar website + careers page + LinkedIn

FASE 4: SCORING + OUTPUT
  Score 0-100 → leads-db.json (actualizar) → markdown del día
```

---

## FASE 1: Descubrimiento de empresas

Ejecutar **las 4 fuentes** en cada invocación. No saltarse ninguna.

### 1.1 — Web Search (fuente principal)

Ejecutar **TODAS** las queries (mezcla español/inglés para máxima cobertura):

| # | Query |
|---|-------|
| 1 | `companies using Flutter in Latin America 2026` |
| 2 | `empresas que usan Flutter en Latinoamérica` |
| 3 | `startups using Flutter Latam remote` |
| 4 | `top Flutter companies Latin America development` |
| 5 | `empresas contratan desarrolladores Flutter remoto` |
| 6 | `Flutter app companies Mexico Colombia Argentina Chile` |
| 7 | `"built with Flutter" startups Latin America` |
| 8 | `Flutter developer remote companies hiring` |
| 9 | `Crunchbase Flutter companies list` |
| 10 | `Wellfound AngelList Flutter startups remote` |
| 11 | `Flutter tech stack companies remote LATAM` |
| 12 | `productos construidos con Flutter Latinoamérica` |

De **cada resultado** extraer:
- `name` — nombre de la empresa
- `website` — URL del sitio web
- `description` — snippet/descripción breve
- `industry` — rubro inferido (fintech, health, e-commerce, etc.)
- `source` — `"web_search"`
- `source_query` — la query que lo encontró
- `country_hint` — país si se menciona

**Nota:** `websearch` puede devolver resultados duplicados entre queries. Se deduplican en FASE 2.

---

### 1.2 — GitHub Organization Search

Buscar organizaciones con repositorios Flutter.

**Método:** Usar `github_search_code` con estas queries:

```
# Orgs con repos Flutter activos
topic:flutter language:dart
```

**También web search para encontrar listas de orgs:**
```
github organizations Flutter Latin America
github.com/orgs Flutter remote
```

De cada organización encontrada extraer:
- `name` — nombre de la org
- `website` — perfil de GitHub (`https://github.com/{org}`)
- `location` — del perfil de la org
- `description` — bio de la org
- `repo_count` — número de repos
- `source` — `"github"`

**Filtrar:** solo organizaciones cuyo perfil indique LATAM o remote-friendly. Si la ubicación no está visible, incluir igual y marcar `location: "unknown"`.

---

### 1.3 — LinkedIn Company Search (chrome-devtools)

Navegar LinkedIn con sesión autenticada del usuario.

**Paso 0:** Verificar/abrir navegador con sesión de LinkedIn (como en `linkedin-hidden-jobs`):
- Usar `chrome-devtools_list_pages` para ver si ya hay páginas abiertas
- Si no hay sesión: abrir `https://www.linkedin.com/feed/` y pedir al usuario que inicie sesión
- Una vez logueado, continuar

**URLs a visitar (una por una):**

```
https://www.linkedin.com/search/results/companies/?keywords=Flutter%20development%20Latin%20America
https://www.linkedin.com/search/results/companies/?keywords=Flutter%20mobile%20apps%20remote
https://www.linkedin.com/search/results/companies/?keywords=Flutter%20startup%20Latam
https://www.linkedin.com/search/results/companies/?keywords=desarrollo%20Flutter%20Latinoam%C3%A9rica
```

**Procedimiento por URL:**
1. Navegar con `chrome-devtools_navigate_page`
2. Esperar 3-5s con `chrome-devtools_wait_for`
3. Tomar snapshot con `chrome-devtools_take_snapshot`
4. Extraer del snapshot para cada empresa en resultados:
   - Nombre de la empresa (link a company page)
   - Descripción corta / tagline
   - Industria (ej: "Software Development", "Financial Services")
   - Tamaño de empresa (ej: "11-50 employees", "51-200 employees")
   - Seguidores
5. Hacer clic en cada empresa para ir a su perfil si se necesita más info
6. Si hay paginación, navegar a página siguiente

**Extraer del perfil de empresa:**
- URL de LinkedIn de la empresa
- Industria detallada
- Tamaño completo
- Si menciona "remote" o "remote-first" en su descripción
- Si tiene careers page link

**Output por empresa:**
```json
{
  "name": "Nombre",
  "linkedin_url": "https://linkedin.com/company/...",
  "industry": "Financial Services",
  "size": "51-200 employees",
  "description": "Snippet de LinkedIn",
  "remote_policy_hint": "remote-first | hybrid | unknown",
  "source": "linkedin"
}
```

---

### 1.4 — Directorios y listados (web search complementario)

Queries adicionales para capturar empresas de directorios especializados:

```
# Product Hunt
Product Hunt Flutter app Latin America startup

# Clutch / GoodFirms top Flutter developers (solo LATAM)
top Flutter app development companies Latin America 2026

# Startup databases
LATAM startups Y Combinator Flutter
YC startups using Flutter
500 startups Latin America mobile app

# Tech blogs
"Flutter" "success story" Latin America
"Flutter" "case study" "app" "Latin America"
```

De cada resultado extraer los mismos campos que en 1.1.

---

### 1.5 — Ensamblar lista completa

Al terminar las 4 fuentes, tendrás un array de empresas (posiblemente con duplicados de distintas fuentes). Pasar a FASE 2.

---

## FASE 2: Deduplicación y normalización

### 2.1 — Cargar DB existente

Leer `/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/empresas-target/leads-db.json`.

Si no existe, inicializar como:
```json
{
  "companies": [],
  "last_updated": "",
  "total_runs": 0
}
```

### 2.2 — Normalizar nombres

Para cada empresa candidata, crear un `name_key`:
- Minúsculas
- Sin tildes
- Sin caracteres especiales
- Sin espacios extra
- Sin "S.A.", "S.A.S.", "Inc.", "LLC", "Ltda.", "Corp.", "S de RL", "S.L.", "SAS" al final

### 2.3 — Cruce contra DB

Por cada candidata:
- Si `name_key` NO existe en DB → agregar como nueva (con `status: "new"`, `first_seen: today`)
- Si `name_key` YA existe → **no duplicar**. Actualizar `last_checked: today`. Si la nueva fuente aporta más datos (LinkedIn URL, careers page, etc.), fusionar campos faltantes.

### 2.4 — Formato común

Toda empresa nueva debe tener esta estructura:

```json
{
  "name": "Nombre Empresa",
  "name_key": "nombre-empresa",
  "website": "https://ejemplo.com",
  "industry": "Fintech | Health | E-commerce | ...",
  "location": "Ciudad, País | unknown",
  "size": "11-50 | 51-200 | 201-1000 | 1000+ | unknown",
  "funding": "Bootstrapped | Seed | Series A | Series B+ | unknown",
  "tech_stack": ["Flutter", "Dart", "Firebase", "..."],
  "uses_flutter": "yes | likely | unknown",
  "remote_policy": "full-remote | hybrid | on-site | unknown",
  "product_description": "App/servicio que ofrece...",
  "sources": ["web_search", "github"],
  "source_queries": ["query que lo encontró"],
  "linkedin_url": "",
  "careers_url": "",
  "github_url": "",
  "score": 0,
  "status": "new",
  "first_seen": "YYYY-MM-DD",
  "last_checked": "YYYY-MM-DD",
  "website_analysis": "",
  "notes": ""
}
```

**Campos obligatorios:** `name`, `name_key`, `website` (o motivo de por qué no tiene), `source`, `status`, `first_seen`, `last_checked`.

### 2.5 — Dedup central (historial del proyecto)

Además de `leads-db.json`, registra cada empresa nueva en
`/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/estado/historial.json`
(categoría `empresas`, clave = dominio o nombre normalizado) usando el helper:

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/estado")
from tracker import Historial
h = Historial()
# consultar: h.is_known("empresas", dominio)
# registrar: h.add("empresas", dominio, meta={"nombre": ..., "url": website, "score": score})
EOF
```

Esto garantiza que `prospectar-clientes`, `flutter-employers` y el
orquestador nunca repitan la misma empresa entre sí.

---

## FASE 3: Enriquecimiento (chrome-devtools)

Procesar máximo **5-8 empresas** por ejecución (las de mayor score potencial, priorizando las que tienen website).

Para CADA empresa:

### 3.1 — Visitar website

1. Abrir nueva página con `chrome-devtools_new_page` apuntando al website
2. Esperar carga (usar `chrome-devtools_wait_for` con timeout 10s, si falla continuar)
3. Tomar screenshot con `chrome-devtools_take_screenshot`
4. Analizar visualmente:
   - **Diseño:** ¿Moderno o anticuado? ¿Responsive?
   - **Tech stack perceptible:** ¿SPA? ¿WordPress? ¿HTML estático?
   - **¿Menciona Flutter?** Buscar en el texto visible "Flutter", "Dart", "app", "mobile"
   - **Producto:** ¿Qué ofrece realmente la empresa?
   - **¿Es agencia o producto?** Si es agencia/consultora → marcar `notes: "Agencia/consultora - bajo prioridad"` y bajar score

5. Si la empresa es **producto** (tiene su propia app/servicio):
   - Buscar menú de navegación con "Careers", "Jobs", "Trabaja con nosotros", "Únete"
   - Si existe, navegar a careers page
   - Extraer vacantes: ¿tienen posiciones abiertas para Flutter/Mobile?
   - Registrar `careers_url` y si hay vacantes relevantes

6. Cerrar página con `chrome-devtools_close_page`

### 3.2 — LinkedIn (si hay linkedin_url)

1. Abrir nueva página con URL de LinkedIn de la empresa
2. Tomar snapshot
3. Confirmar tamaño, industria, remote policy
4. Verificar si tienen tag de "Remote" en su perfil
5. Cerrar página

### 3.3 — Registrar análisis

Guardar en `website_analysis`:
```
"Sitio web moderno SPA, mencionan Flutter en su stack tecnologico, tienen careers page con vacante abierta para Flutter Developer. Empresa producto (app de fintech para LATAM). 51-200 empleados. Remote-first segun LinkedIn."
```

---

## FASE 4: Scoring + Output

### 4.1 — Algoritmo de scoring (0-100)

Asignar score a **todas** las empresas nuevas (y re-scorear existentes si hay datos nuevos).

| Criterio | Max pts | Evaluación |
|----------|---------|------------|
| **Usa Flutter** | 40 | `confirmed=40`, `likely=25`, `unknown=10`, agencia=5 |
| **Remoto-friendly** | 20 | `full-remote=20`, `hybrid=10`, `on-site=0`, `unknown=5` |
| **Hiring signals** | 15 | Vacante activa Flutter=15, vacante genérica mobile=8, no detectada=0 |
| **LATAM-based** | 15 | HQ LATAM=15, Global con equipo LATAM=10, Global=5 |
| **Es producto** | 10 | Producto propio=10, mixto=5, agencia=0 |

**Reglas de negocio:**
- Si `uses_flutter` es `unknown` Y `website_analysis` no disponible → score máximo 30 hasta enriquecer
- Si se detecta que es agencia/consultora → **penalizar**: score máximo 40 (no es target primario)
- Si tiene vacante activa para Flutter → sumar 15 extra (bonus adicional sobre el máximo)

**Umbrales:**

| Nivel | Score | Acción |
|-------|-------|--------|
| 🔥 **Hot** | ≥ 70 | Prioridad alta. Tienen Flutter + remoto + posible hiring. Listas para cv-apply. |
| 🟡 **Warm** | 40 — 69 | Seguimiento. Falta información o señal débil. Enriquecer en próxima ejecución. |
| ⚪ **Cold** | < 40 | Guardar para futura investigación. Baja prioridad. |

### 4.2 — Actualizar DB

1. Agregar empresas nuevas con su score
2. Actualizar `last_checked` de todas las procesadas
3. Actualizar `last_updated` con la fecha actual
4. Incrementar `total_runs`
5. Guardar `leads-db.json` completo

### 4.3 — Generar markdown del día

```markdown
# Empresas Target — Flutter — {YYYY-MM-DD}

> Discovery: startups + empresas LATAM + globales remote-first
> Fuentes: Web Search, GitHub, LinkedIn, Directorios
> Total empresas activas: {n} | Nuevas hoy: {n} | Ejecución #{run}

---

## 🔥 Hot (score ≥ 70)

### 1. {Nombre Empresa}
- **Industria:** {industry}
- **Ubicación:** {location} | **Tamaño:** {size}
- **Stack:** {tech_stack} | **Flutter:** {confirmed / likely / unknown}
- **Remote:** {full-remote / hybrid / on-site}
- **Funding:** {funding}
- **🏢** [{website}]({website}) | **💼** [{careers}]({careers_url})
- **LinkedIn:** [{linkedin_url}]({linkedin_url})
- **GitHub:** [{github_url}]({github_url})
- **Producto:** {product_description}
- **Señales hiring:** {vacantes detectadas / no detectadas}
- **Website:** {website_analysis}
- **Score:** {n}/100 🔥
- **Fuente:** {sources}
- **Visto por primera vez:** {first_seen}
`[Aplicar con cv-apply]`

### 2. ...

---

## 🟡 Warm (40 — 69)

### {n}. {Nombre Empresa}
- ...

---

## ⚪ Cold (< 40)

### {n}. {Nombre Empresa}
- ...

---

## 📊 Resumen

| Categoría | Cantidad |
|-----------|----------|
| 🔥 Hot (≥70) | {n} |
| 🟡 Warm (40-69) | {n} |
| ⚪ Cold (<40) | {n} |
| **Total activas** | **{n}** |
| Nuevas hoy | {n} |

---

## 🎯 Próximos pasos sugeridos

1. Revisar empresas **Hot** → elegir una y aplicar con `cv-apply`
2. Empresas **Warm** → investigar más (visitar website, buscar hiring signals)
3. Volver a ejecutar en unos días para descubrir más empresas

> Para aplicar a una empresa: dime "aplica a {nombre}" o "cv-apply con {url_vacante}" y genero el CV optimizado + carta.
> Para contactar reclutadores: usa `linkedin-outreach` con el perfil del recruiter.
```

---

## Ejecución

Cuando el usuario invoque la skill (ej: "busca empresas flutter", "flutter-employers", "encuentra empresas target"):

```bash
# El agente ejecuta TODO el flujo en orden:
# FASE 1 → Descubrimiento (4 fuentes)
# FASE 2 → Dedup + normalización
# FASE 3 → Enriquecimiento (top 5-8)
# FASE 4 → Scoring + output markdown + guardar DB
```

### Límites por ejecución

| Recurso | Límite |
|---------|--------|
| Web search queries | Máximo 12 por ejecución (todas las de 1.1 + complementarias de 1.4) |
| GitHub queries | Máximo 3 por ejecución |
| LinkedIn navegación | Máximo 4 URLs de search + clicks en resultados |
| Chrome pages abiertas | Máximo 1 a la vez (cerrar después de cada visita) |
| Websites visitados (FASE 3) | Máximo 8 por ejecución |
| Empresas nuevas por tanda | Sin límite fijo, pero priorizar calidad sobre cantidad |

### Manejo de errores por fuente

- **Web search:** Si una query devuelve 0 resultados, continuar con la siguiente. No detener.
- **GitHub:** Si `github_search_code` falla (rate limit), omitir y continuar.
- **LinkedIn:** Si no hay sesión activa, omitir LinkedIn y continuar con las otras fuentes.
- **Directorios:** Si no hay resultados, omitir.

Si **todas** las fuentes fallan, mostrar mensaje de error y sugerir reintentar más tarde.

---

## Post-ejecución

Cuando el usuario vea la lista y quiera actuar:

1. **"Aplica a {nombre}"** o **"cv-apply con {url_vacante}"** → cargar skill `cv-apply` y generar CV + carta + PDF
2. **"Contactar {nombre}"** o **"linkedin-outreach {perfil}"** → cargar skill `linkedin-outreach` para generar mensaje personalizado
3. **"Marcar aplicado {nombre}"** → actualizar `status` a `applied` en `leads-db.json`
4. **"Ver historial"** → mostrar resumen de `leads-db.json`
5. **"Analizar {url}"** → agregar empresa manualmente y ejecutar FASE 3 + 4 solo para esa

### Comandos rápidos

| Comando | Acción |
|---------|--------|
| `"flutter-employers"` | Ejecutar pipeline completo (diario/semanal) |
| `"target {nombre}"` | Mostrar datos de una empresa específica |
| `"aplica {nombre}"` | Iniciar cv-apply para esa empresa |
| `"marcar {nombre} applied"` | Actualizar DB |
| `"ver targets"` | Mostrar resumen DB |
| `"analizar {url}"` | Agregar empresa manual |

---

## Estado persistente: leads-db.json

Estructura completa del JSON:

```json
{
  "last_updated": "2026-07-07",
  "total_runs": 5,
  "companies": [
    {
      "name": "Nomad Studio",
      "name_key": "nomad-studio",
      "website": "https://nomadstudio.com",
      "industry": "Fintech",
      "location": "Ciudad de México, MX",
      "size": "11-50",
      "funding": "Seed",
      "tech_stack": ["Flutter", "Dart", "Firebase", "Node.js"],
      "uses_flutter": "yes",
      "remote_policy": "full-remote",
      "product_description": "App de fintech para remesas LATAM",
      "sources": ["web_search", "linkedin"],
      "source_queries": ["Flutter startups Mexico", "linkedin search Flutter companies"],
      "linkedin_url": "https://linkedin.com/company/nomadstudio",
      "careers_url": "https://nomadstudio.com/careers",
      "github_url": "https://github.com/nomadstudio",
      "score": 87,
      "status": "new | visited | applied | rejected | hired",
      "first_seen": "2026-07-07",
      "last_checked": "2026-07-07",
      "website_analysis": "Sitio moderno SPA, mencionan Flutter en tech stack, careers page con vacante Flutter Dev",
      "notes": ""
    }
  ]
}
```

### Flujo de persistencia

1. Al iniciar, leer `leads-db.json` (si no existe, crear estructura vacía)
2. FASE 2: cotejar candidatas vs DB por `name_key`
3. FASE 4: actualizar scores y `last_checked` incluso para empresas existentes si hay datos nuevos
4. Guardar DB actualizada

Esto permite:
- No repetir empresas en ejecuciones sucesivas
- Acumular histórico de empresas descubiertas
- Rastrear estado (new → visited → applied → rejected → hired)
- Re-evaluar empresas existentes cuando se tenga más datos
