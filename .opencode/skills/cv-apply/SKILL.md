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
  -V geometry=margin=1in \
  --standalone
```

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