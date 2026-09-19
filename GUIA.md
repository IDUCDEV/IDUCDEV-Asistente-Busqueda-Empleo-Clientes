# IDUCDEV — Asistente de Búsqueda de Empleo y Clientes

Asistente personal que hace por ti **todo el proceso tedioso y
repetitivo** de buscar empleo y clientes: rastrea vacantes en 7+ fuentes,
descubre empresas y leads, prepara CVs optimizados ATS y mensajes de
contacto. **Y nunca te vuelve a mostrar lo que ya viste.**

---

## Cómo se usa (para ti, el humano)

No tienes que saber de skills ni de carpetas. Solo habla con el
asistente como con una persona. Frases que entiende:

| Di esto | Qué hace por ti |
|---------|-----------------|
| **"Haz la ronda de hoy"** | Busca vacantes nuevas (7 fuentes) + proyectos Workana + posts ocultos de LinkedIn + leads de clientes + empresas target. **Omite todo lo que ya viste** y te deja un resumen. |
| **"Solo empleos"** | Solo la parte de búsqueda de trabajo. |
| **"Solo clientes"** | Solo descubrir potenciales clientes. |
| **"¿Qué hay nuevo?"** | Te dice lo pendiente de revisar sin volver a buscar. |
| **"Aplica a {x}"** | Genera CV optimizado ATS + carta + PDF para esa vacante, con el link pegado. |
| **"Contacta a {perfil}"** | Genera el mensaje personalizado para ese reclutador/empresa en LinkedIn. |
| **"Marca {x} como aplicado"** | Lo registra como hecho para no repetirlo. |
| **"Guía"** | Vuelve a mostrarte este documento resumido. |

### Ejemplos reales

```
"Haz la ronda de hoy"
"¿Qué hay nuevo?"
"Solo empleos"
"aplica a esta vacante: <pega el texto o link>"
"contacta a https://www.linkedin.com/in/xxx"
"marca Flutter Developer en GetOnBoard como aplicado"
"¿algún cliente nuevo esta semana?"
```

---

## Qué hace exactamente por ti

1. **Busca vacantes** Flutter/Dart remotas LATAM en LinkedIn, GetOnBoard,
   Himalayas, RemoteJobs.org, Career Nest, Jobicy y Computrabajo, más
   proyectos freelance en Workana y posts con vacantes ocultas en LinkedIn.
2. **Busca clientes**: negocios venezolanos que necesiten web/apps/n8n y
   empresas (LATAM y globales remote-first) que usan Flutter.
3. **No repite nada**: todo lo que has visto queda registrado en
   `estado/historial.json`. Si una vacante o cliente vuelve a aparecer,
   se omite (te dice cuántos omitió).
4. **Te prepara para actuar**: CV optimizado por vacante, carta, PDF, y
   mensaje de outreach listo para copiar/pegar en LinkedIn.
5. **Te deja un resumen diario** en `informes/`.

---

## Dónde aparecen las cosas

Todo queda guardado en carpetas ordenadas, listas para ti:

| Carpeta | Contenido |
|---------|-----------|
| `vacantes/` | Vacantes del día (buscador automático) |
| `vacantes-workana/` | Proyectos freelance de Workana |
| `vacantes-ocultas/` | Vacantes de posts de LinkedIn |
| `clientes-potenciales/` | Leads de negocio con scoring |
| `empresas-target/` | Empresas donde aplicar |
| `mensajes-outreach/` | Mensajes de contacto generados |
| `CV_*.md` / `*.pdf` | CVs y PDFs listos para enviar |
| `informes/` | Resumen diario de la ronda |
| `estado/historial.json` | El "no repitas esto" del asistente |

---

## ¿Cada cuánto se usa?

- **Diario (ideal):** `"Haz la ronda de hoy"` → busca y te deja el resumen.
- **Semanal:** clientes y empresas target (descubrir cosas nuevas).
- **Cuando decidas:** aplicar a una vacante o contactar a alguien.

El asistente pide autorización antes de abrir el navegador (necesario
para LinkedIn y para visitar websites). El resto lo hace solo.

---

## Restaurar en una computadora nueva

1. Clona el repo y ábrelo con opencode.
2. Restaura las skills:
   ```bash
   cp -r skills-backup/* ~/.opencode/skills/
   ```
3. Verifica que exista `estado/historial.json` (si no, se crea solo).
4. Instala dependencias: `pandoc`, `fonts-liberation`, `python3`.

---

> 📂 Este proyecto vive en:
> `~/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes`