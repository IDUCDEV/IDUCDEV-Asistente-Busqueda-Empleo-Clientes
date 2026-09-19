---
name: asistente-empleo-clientes
description: Orquestador central de búsqueda de empleo y clientes. Delegado único para TODO el proceso tedioso: buscar vacantes (job-search, workana-search, linkedin-hidden-jobs), descubrir empresas (flutter-employers), prospectar clientes (prospectar-clientes), generar outreach (linkedin-outreach) y preparar CVs (cv-apply). NUNCA repite nada: consulta y actualiza estado/historial.json. Genera un resumen diario en informes/.
---

# Asistente IDUCDEV — Empleo + Clientes

Cuando el usuario te pida algo de "buscar empleo", "buscar clientes",
"hacer la ronda", "qué hay nuevo", "aplicar", "contactar" — **tú eres la
puerta de entrada**. No invocas solo una skill: decides qué sub-skills
necesita su petición, las ejecutas en orden y todo pasa por la
**base de datos central de deduplicación**.

## Archivos de referencia

- **Proyecto:** `/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/`
- **Historial central (dedup):** `/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/estado/historial.json`
- **Helper del historial:** `/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/estado/tracker.py`
- **Informes diarios:** `/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/informes/{YYYY-MM-DD}-resumen.md`
- **Guía de uso (para el usuario):** `/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/GUIA.md`
- **CV base:** `/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/isaac-urdaneta-base.md`

## Principio de oro: NUNCA repetir

Antes de mostrarle al usuario cualquier vacante, empresa o cliente,
debes comprobar que no esté ya en `estado/historial.json`. Al terminar,
registra todo lo nuevo en el historial.

### Cómo consultar el historial (Python)

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/estado")
from tracker import Historial
h = Historial()
print("vacantes:", h.stats()["vacantes"])
print("empresas:", h.stats()["empresas"])
print("clientes:", h.stats()["clientes"])
EOF
```

### Claves por categoría (mismo criterio en todas las skills)

| Categoría | Clave | Meta útil |
|-----------|-------|-----------|
| `vacantes` | `empresa_normalizada::titulo_normalizado` | empresa, titulo, url, fuente |
| `empresas` | dominio o nombre normalizado | url, score |
| `clientes` | dominio o nombre del negocio | rubro, score, web |
| `proyectos_workana` | slug del proyecto | titulo, url, budget |
| `posts_linkedin` | URL del post | autor, snippet |
| `outreach` | URL del perfil | nombre, empresa |

---

## Órdenes que entiende

### 1. "Haz la ronda de hoy" (empleos + clientes)
Ejecuta el pipeline completo en este orden, SIN repetir nada:

1. `job-search` → vacantes (`python3 /home/iducdev/.opencode/skills/job-search/job_search.py`)
2. `workana-search` → proyectos freelance (`python3 /home/iducdev/.opencode/skills/workana-search/workana_search.py`)
3. `linkedin-hidden-jobs` → mercado oculto de LinkedIn (navegador)
4. `prospectar-clientes` → leads de negocio VE
5. `flutter-employers` → empresas target (descubrimiento semanal)

Al terminar cada skill, leer su output (`.md` generado) y **construir
`informes/{YYYY-MM-DD}-resumen.md`** que consolide: cuántas vacantes
nuevas, cuántos clientes nuevos, cuántos omitidos por repetidos, y el
top 5 de cada categoría con sus links.

### 2. "Solo empleos" / "solo clientes"
- Empleos → pasos 1, 2, 3
- Clientes → pasos 4, 5
Genera el informe parcial igualmente.

### 3. "¿Qué hay nuevo?" / "estado"
Lee `estado/historial.json` y muestra resumen por categoría con fechas.
No ejecuta búsquedas nuevas.

### 4. "Aplica a {vacante/empresa}"
Carga `cv-apply` (pégame la descripción o URL si no la tengo) → genera
CV optimizado ATS + carta + PDF. Al generar, actualiza `estado` de esa
vacante a `applied` en el historial.

### 5. "Contacta a {perfil/empresa}"
Carga `linkedin-outreach` → genera mensaje personalizado. Al generar,
registra el perfil en categoría `outreach` con estado `enviado`.

### 6. "Marca X como aplicado/descartado/contactado"
Actualiza `estado` en el historial:
```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/estado")
from tracker import Historial
h = Historial()
h.set_state("vacantes", "empresa::titulo", "applied")
EOF
```

### 7. "Guía" / "cómo se usa esto"
Lee y muestra el contenido de `GUIA.md` de forma resumida.

---

## Registro del historial tras cada skill

Tras cada ejecución que produzca resultados nuevos, verifica (y si
falta, añade) las claves en `historial.json`:

- vacantes → categoría `vacantes`
- empresas descubiertas → categoría `empresas`
- clientes prospección → categoría `clientes`
- posts de LinkedIn procesados → categoría `posts_linkedin`
- outreach generado → categoría `outreach`

Los scripts de `job-search` y `workana-search` ya deduplican solos
contra el historial; verifica su salida `---SKIPPED---`.

---

## Reglas de interacción

1. **Siempre confirma con el usuario antes de invadir su navegador**
   (linkedin-hidden-jobs, flutter-employers y prospectar-clientes abren
   chrome). Pregunta: "¿Abro el navegador para X?".
2. Para `cv-apply` y `linkedin-outreach`, pide autorización y datos
   mínimos que falten (URL de la vacante / perfil).
3. Mantén las respuestas concisas en el chat; los detalles van en los
   `.md` y en el informe diario.
4. Si una fuente falla (red, sesión), continúa con las demás y anótalo
   en el informe; nunca bloquees la ronda completa.

---

## Verificación rápida tras la ronda

```bash
python3 /home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/estado/tracker.py stats
```