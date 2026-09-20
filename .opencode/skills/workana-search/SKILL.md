---
name: workana-search
description: Busca proyectos freelance en Workana (IT & Programming > Mobile Development). Scrapea resultados, marca con ✅ los que tienen Flutter/Dart, y genera listado markdown para aplicar con cv-apply.
---

# Skill: workana-search

Buscador de proyectos mobile en Workana. Cuando el usuario invoque esta skill, ejecuta:

```bash
python3 .opencode/skills/workana-search/workana_search.py
```

Esto orquesta todo el workflow (fetch, parse, filtros, markdown).  
El script imprime la ruta del archivo generado (en `vacantes-workana/{fecha}.md`),
conteos y errores.  
Muéstrale el resultado al usuario e indica que puede aplicar con `cv-apply`.

Si invocas la skill dentro de la ronda, ejecútala vía orquestador:
```bash
python3 estado/orquestador.py ronda --empleos
```

## Fuente

**Workana** — Categoría IT & Programming > Mobile Development

**URL:**
```
https://www.workana.com/jobs?category=it-programming&subcategory=mobile-development&page=N
```

**Formato:** HTML con JSON embebido en `:results-initials` prop del componente `<search>`.

**Extraer por cada proyecto:**
- `slug` — identificador único
- `title` — título del proyecto
- `authorName` — nombre del cliente
- `budget` — presupuesto (USD)
- `postedDate` — fecha de publicación
- `skills[]` — lista de tecnologías
- `isUrgent` — si es urgente
- `isHourly` — si es por hora
- `description` — descripción corta

**Filtro Flutter/Dart:** Se marca con ✅ si el título o las habilidades contienen "flutter", "dart", "cross-platform" o "multiplataforma".

## Output

```
vacantes-workana/{YYYY-MM-DD}.md
```

Si se invoca varias veces el mismo día, sobrescribe el archivo del día.

## Post-búsqueda

Cuando el usuario vea la lista y quiera aplicar a un proyecto:

1. Usuario dice: "aplica a este proyecto" y pasa el link o slug
2. Cargar la skill `cv-apply`
3. El workflow de `cv-apply` genera la propuesta personalizada
4. Marcar el proyecto como `applied`:
   ```bash
   python3 estado/orquestador.py marcar proyectos_workana "<slug>" applied
   ```

## Pipeline

Búsqueda → Listado markdown → Usuario elige → `cv-apply` → Propuesta Workana