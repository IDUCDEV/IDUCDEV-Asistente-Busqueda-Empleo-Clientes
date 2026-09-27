---
name: hidden-jobs-web
description: Busca el "hidden job market" de Flutter por web cuando no es parseable por script: mobile.career (filtro LATAM+Flutter, API con auth → navegador), Y Combinator Work at a Startup, X/Twitter, y descubrimiento de empresas en tableros ATS vía site:boards.*. Genera resultados/vacantes-web/{fecha}.md y registra las empresas halladas en estado/empresas_registry.json.
---

# hidden-jobs-web — Flutter por web (lo que el script no alcanza)

## Cuándo usarla

`job_search.py` corre solo y sin navegador. Estas fuentes **no** son parseables
por HTTP, así que requieren `websearch` / `chrome-devtools` con la sesión del
usuario. No intentes automatizarlas en un script.

Antes de abrir el navegador: **autorización previa del usuario** (regla del repo).

## Fuentes (y las que ya se descartaron, no repetir)

| Fuente | Cómo | Estado |
|---|---|---|
| **mobile.career** | `websearch` + `chrome-devtools` en `/locations/latam` | ✅ Tiene filtros Flutter + LATAM + salario + nivel. `/api/v1/jobs` → **401**, hay que leer la vista |
| **Tableros ATS vía búsqueda** | `websearch` con `site:boards.greenhouse.io flutter`, `site:jobs.ashbyhq.com flutter`, `site:jobs.lever.co flutter` | ✅ Descubre empresa **y** slug del tablero |
| **Y Combinator** | `chrome-devtools` en `workatastartup.com/companies`, filtrar Flutter | ✅ Sesión del usuario |
| **X / Twitter** | `websearch` | ⚠ Opcional. Desactivar si 0 resultados dos rondas seguidas |

**Descartadas con evidencia — no volver a intentarlas:**

- **Telegram**: 5 canales probados, 0 mensajes.
- **Reddit / Jobgether / WWR / Devitjobs**: 403 o sin datos.
- **Hacker News**: los "Who is hiring" son de 2015-2020.
- **Arbeitnow**: 0 vacantes Flutter en 325.
- **Remotive con `location=LATAM`**: 0 de 17 vacantes son Flutter.
- **Computrabajo** fuera de los 7 países del script: 403.
- **mobile.career** vía script: 401 (auth).

## Procedimiento

1. Consulta `estado/historial.json` para no repetir lo ya visto
   (`python3 estado/tracker.py stats`).
2. Para cada consulta, **verificar la URL antes de citarla** (200 y contenido real).
3. Extraer: `empresa`, `título`, `url`, `ubicación`, `modalidad`, `salario`, `fecha`.
4. Regla de marcado, igual que en los parsers:
   - Flutter/Dart explícito en el título → vacante normal.
   - Solo móvil o solo en la descripción → `⚠ verificar`.
   - Sin relación → **descartar**, no listar.
5. Escrituras:
   - Vacantes → `resultados/vacantes-web/{fecha}.md` + historial categoría
     `vacantes` (misma clave `empresa::titulo`, para que el dedup sea unificado
     con el script).
   - Empresas nuevas → añadir a `estado/empresas_registry.json` con su
     `careers_url`/slug deducido, para que `empresas_search.py` las sondee.
6. Registrar la fase en la ronda:

```bash
python3 estado/orquestador.py registrar hidden-jobs <archivo> --nuevas N
```

## Privacidad

Sin login ni API keys. Todo por páginas públicas. No usar el Gmail del `.env`
para nada de esta skill.
