---
name: cv-apply
description: Use when the user pastes a job description and wants to evaluate it or generate an ATS-optimized CV and cover letter. Reads recursos/cv/base-isaac-urdaneta.md and recursos/guias/cv-reglas-ats.md from the resource center. Generates .md, .pdf and cover letter into resultados/cv/.
---

# cv-apply — Aplicación automática a vacantes

Cuando el usuario pegue la descripción de una vacante y pida evaluarla o aplicar, ejecuta este workflow completo usando sus archivos de CV base y reglas ATS.

## Referencias del proyecto (rutas relativas a la raíz)
- **CV Base:** `recursos/cv/base-isaac-urdaneta.md` (centro de recursos)
- **Reglas ATS:** `recursos/guias/cv-reglas-ats.md`
- **Output dir:** `resultados/cv/` (CV optimizado + carta + PDF)

## Workflow

### Fase 1: Análisis de la vacante

Lee la vacante que el usuario pegó y extrae:
- **Requisitos técnicos:** frameworks, lenguajes, herramientas, infraestructura, años de experiencia
- **Requisitos funcionales:** responsabilidades, modalidad, ubicación, idiomas
- **Palabras clave ATS:** todas las keywords técnicas y funcionales

### Fase 1.5: Pre-filtro automático (OBLIGATORIO)

**Antes de puntuar nada**, pasa la vacante por el filtro. Existe porque 4
descartes consecutivos (Hansa, Walmart, QiBit, Mars) llegaron porque "Flutter"
aparecía en el texto sin ser el centro del rol:

```bash
python3 estado/filtro_vacante.py \
  --titulo "<título de la vacante>" \
  --empresa "<empresa>" \
  --archivo /tmp/vacante.txt \
  --marcar
```

Guarda el texto de la vacante en un archivo primero (el HTML de la página sirve).
`--marcar` deja la vacante en `descartado` si el veredicto es FAIL.

| Regla | Qué descarta |
|---|---|
| F1 | Flutter/Dart aparece 0 veces en el cuerpo |
| F2 | Flutter aparece solo después de un marcador "deseable / nice to have / plus" |
| F3 | Título `Principal / Lead / Architect / Head / Staff / Director` |
| F4 | Presencial o contrato local (CLT/EPS) declarado **y** sin "remoto" |
| F5 | Exige formación superior **completa** (bloqueante D-08) |
| F6 | Una stack ajena (React Native, Kotlin, .NET, data eng, QA…) domina el cuerpo |
| F10 | **Angular** declarado 2+ veces — no está en tu base (0 menciones) |
| F11 | Señales de perfil web (TypeScript/NPM/Vue/Next.js) superan a Flutter en el cuerpo |
| F7 | *(aviso, no descarta)* Inglés avanzado / B2+ — el usuario ha aplicado igual |
| F8 | *(aviso)* Título Junior — quedaría por encima |
| F9 | *(aviso)* Pide muchos más años de los que tienes |

**Si el veredicto es FAIL:** no hagas el análisis completo ni generes CV. Reporta
las reglas que dispararon y listo. **Si es PASS con avisos:** reporta los avisos
al usuario y sigue a Fase 2 normalmente.

Regenera/valida el filtro con `python3 estado/test_filtro_vacante.py`.

### Fase 2: Decisión "¿Vale la pena?"

Mapea la vacante contra el CV base con estos criterios:

| Factor | Peso | Evaluación |
|---|---|---|
| Tecnología principal coincide (Flutter/Dart) | 40% | ¿La vacante pide Flutter como skill principal? |
| Backend/cloud match | 15% | ¿Pide Java/Spring/C#/.NET? (penaliza fuerte — sin experiencia). ¿Pide Supabase/Firebase/Serverpod/PostgreSQL/Node? (coincide — tu stack real) |
| Experiencia requerida vs real | 15% | Si pide 5+ años y tienes 2, pero es Flutter puro, se puede argumentar |
| Ubicación/modalidad | 15% | ¿Remoto? ¿Híbrido en otro país? ¿Reubicación? |
| Inglés | 10% | ¿Pide inglés avanzado? (tienes B1) |
| Otros gaps | 5% | Tecnologías adicionales que no dominas |

**Reglas de decisión:**
- **Flutter es el core de la vacante Y match ≥ 60%** → ✅ Vale la pena
- **Flutter es secundario o match < 60%** → ❌ No vale la pena

Presenta al usuario un resumen claro con:
- Match general (%)
- Principales coincidencias
- Principales gaps
- Recomendación final (sí/no)

### Fase 3: Generación del CV optimizado

Si vale la pena, sigue las reglas de `recursos/guias/cv-reglas-ats.md` al pie de la letra:

1. **Resumen Profesional:** reescribe para enfatizar requisitos de la vacante, incluir keywords principales en primeras 2 líneas, mencionar años y modalidad
2. **Habilidades Técnicas:** reordenar (primero lo requerido), agregar lo que falte pero se domine
3. **Experiencia:** bullets reescritos con verbos de acción, métricas alineadas a la vacante
4. **Proyectos:** seleccionar los más relevantes, reescribir énfasis

**Adaptación DevOps según el rol:**
- **Solo mobile** → reducir DevOps a (Docker, Makefile, CI/CD), omitir Dokploy/SSH
- **Mobile + DevOps/infra** → mantener y alinear descripciones
- **Solo infra/DevOps** → pivotar: infraestructura como skill principal

**Formato ATS-safe:**
- Headers simples (`##`)
- Listas con guiones (`-`)
- Sin tablas, columnas, imágenes, footnotes
- Sin bold ni énfasis innecesario que confunda al parser

**Idioma:** alineado al de la vacante (español, portugués o inglés)

**Nombre de archivo:** `{cv-base}-{rol}-{empresa}.md`

### Fase 4: Carta de presentación

Genera una carta de presentación en el mismo idioma de la vacante, en texto plano para copiar y pegar. Incluir:
- Asunto con el nombre del puesto y empresa
- Presentación personal (nombre, perfil)
- 2-3 párrafos destacando experiencia relevante para la vacante
- Cierre con datos de contacto

### Fase 5: Generación de PDF

Ejecuta pandoc para convertir el markdown a PDF:

```bash
pandoc "{md_path}" -o "{pdf_path}" \
  -V mainfont="Liberation Sans" \
  -V fontsize=11pt \
  -V geometry=margin=0.7in \
  --standalone \
  --pdf-engine=xelatex
```

**`--pdf-engine=xelatex` es obligatorio.** Con el motor por defecto (`pdflatex`)
las variables `mainfont` y `fontsize` se ignoran en silencio y el PDF sale en
Latin Modern serif a 10pt. `xelatex` sí las respeta.

Verifica el resultado (un CV de 2 páginas debe dar `Pages: 2`, carta 1):

```bash
pdfinfo "{pdf_path}" | grep -i '^Pages'
```

Si el CV se pasa de 2 páginas, baja el margen a `0.6in` antes de recortar
contenido — nunca elimines métricas verificables (regla R1).

### Fase 6: Reporte final

Informa al usuario:
- ✅/❌ Decisión de aplicar
- Ruta de los archivos generados (.md y .pdf)
- Cover letter en texto (para copiar)
- Resumen breve de por qué

## Integración con el estado del asistente

Después de generar el CV y aplicar, marcar la vacante en el historial para
que el orquestador cree el seguimiento automático (D+7):

```bash
python3 estado/orquestador.py marcar vacantes "<empresa::titulo>" applied
```

## Notas
- Si no existen `recursos/cv/base-isaac-urdaneta.md` o `recursos/guias/cv-reglas-ats.md`, revisar `recursos/INDICE.md`
- No modificar nunca los archivos base (los actualiza el usuario)
- Los outputs se guardan en `resultados/cv/`
- Verificar que pandoc está disponible antes de convertir