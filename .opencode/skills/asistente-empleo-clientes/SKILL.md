---
name: asistente-empleo-clientes
description: Orquestador central de búsqueda de empleo y clientes. Delegado único para TODO el proceso tedioso: buscar vacantes (job-search, workana-search, linkedin-hidden-jobs), descubrir empresas (flutter-employers), prospectar clientes (prospectar-clientes), generar outreach (linkedin-outreach) y preparar CVs (cv-apply). NUNCA repite nada: consulta y actualiza estado/historial.json. Genera un resumen diario en resultados/informes/.
---

# Asistente IDUCDEV — Empleo + Clientes

Cuando el usuario te pida algo de "buscar empleo", "buscar clientes",
"hacer la ronda", "qué hay nuevo", "aplicar", "contactar" — **tú eres la
puerta de entrada**. No invocas solo una skill: decides qué sub-skills
necesita su petición, las ejecutas en orden y todo pasa por la
**base de datos central de deduplicación**.

Todas las rutas de este documento son **relativas a la raíz del proyecto**
(openCode se ejecuta desde ahí). Los scripts de las skills viven en
`.opencode/skills/<skill>/`.

## Archivos de referencia

- **Raíz del proyecto:** `.` (marcada con `.iducdev-root`; ser resuelve también vía `IDUCDEV_PROJECT_DIR`)
- **Config de rutas:** `estado/config.py` (fuente única, no hardcodear rutas)
- **Orquestador CLI:** `estado/orquestador.py` (ronda, marcar, tareas, seguimientos, informe)
- **Cola de envíos:** `estado/cola_envios.json` (CLI: `estado/cola_envios.py`)
- **Historial central (dedup):** `estado/historial.json` (helper: `estado/tracker.py`)
- **Bandeja de tareas:** `estado/tareas.json`
- **Bitácora de rondas:** `estado/rondas.json`
- **Informes diarios:** `resultados/informes/{YYYY-MM-DD}-resumen.md`
- **Centro de recursos (consultar antes):** `recursos/INDICE.md`
- **Guía de uso (único documento, para el usuario):** `GUIA.md`
- **CV base:** `recursos/cv/base-isaac-urdaneta.md` | **Reglas ATS:** `recursos/guias/cv-reglas-ats.md`
- **Guía de uso (único documento, para el usuario):** `GUIA.md`

## Principio de oro: NUNCA repetir

Antes de mostrarle al usuario cualquier vacante, empresa o cliente,
debes comprobar que no esté ya en `estado/historial.json`. Al terminar,
registra todo lo nuevo en el historial.

### Cómo consultar el historial (Python)

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "estado")
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

1. `job-search` → vacantes (`python3 .opencode/skills/job-search/job_search.py`)
2. `workana-search` → proyectos freelance (`python3 .opencode/skills/workana-search/workana_search.py`)
3. `linkedin-hidden-jobs` → mercado oculto de LinkedIn (navegador)
4. `prospectar-clientes` → leads de negocio VE
5. `flutter-employers` → empresas target (descubrimiento semanal)

**Si es una ronda sin navegador**, ejecuta:
```bash
python3 estado/orquestador.py ronda --empleos
```
Esto lanza los scripts 1 y 2, registra las fases en `estado/rondas.json`
y genera `resultados/informes/{YYYY-MM-DD}-resumen.md`.

Después de cada fase de **navegador** ejecutada manualmente (pasos 3-5),
regístrala para que el informe la consolide:
```bash
python3 estado/orquestador.py registrar linkedin-hidden-jobs resultados/vacantes-ocultas/{fecha}-hidden.md --nuevas N --omitidas M
python3 estado/orquestador.py registrar prospectar-clientes resultados/clientes-potenciales/{fecha}-leads.md --nuevas N --omitidas M
python3 estado/orquestador.py registrar flutter-employers resultados/empresas-target/{fecha}-empresas.md --nuevas N --omitidas M
```

Al terminar todas las fases, regenera/consolida el resumen:
```bash
python3 estado/orquestador.py informe
```

### 2. "Solo empleos" / "solo clientes"
- Empleos → pasos 1, 2, 3 (`python3 estado/orquestador.py ronda --empleos`)
- Clientes → pasos 4, 5
Genera el informe parcial igualmente con `registrar` + `informe`.

### 3. "¿Qué hay nuevo?" / "estado"
```bash
python3 estado/orquestador.py estado
```
Muestra historial por categoría + bandeja de tareas + seguimientos vencidos.
No ejecuta búsquedas nuevas.

### 4. "Aplica a {vacante/empresa}"
Carga `cv-apply` (pégame la descripción o URL si no la tengo) → genera
CV optimizado ATS + carta + PDF. Al generar, actualiza `estado` de esa
vacante a `applied` en el historial:
```bash
python3 estado/orquestador.py marcar vacantes "empresa::titulo" applied
```

### 5. "Contacta a {perfil/empresa}" (empleo)
Carga `linkedin-outreach` → genera mensaje personalizado. Al generar,
registra el perfil en categoría `outreach` con estado `enviado` y el
orquestador creará **automáticamente** la tarea de seguimiento (D+3):
```bash
python3 estado/orquestador.py marcar outreach "<url-del-perfil>" enviado
```

### 5b. "Contacta a {cliente}/{lead}" (ventas)
Carga `contactar-clientes` → genera mensaje de venta personalizado
(whatsapp/email/linkedin) desde `leads-db.json` y **lo encola** en
`estado/cola_envios.json` (status del lead: `en_cola`). NO marques
todavía `contactado`: eso ocurre al enviar.

### 5c. "Envía los pendientes" / `/enviar`
Carga `enviar-clientes` → ronda **uno por uno**: muestra cada mensaje de
la cola, el usuario lo valida (ok/modificar/saltar/parar) y se envía por
canal (email automático, WhatsApp Web con navegador autorizado, LinkedIn
semi) respetando límite diario y pausas. Tras cada envío efectivo:
```bash
python3 estado/cola_envios.py marcar <id> enviado
python3 estado/orquestador.py marcar clientes "<clave>" contactado
```
(el `contactado` crea la tarea de seguimiento D+3).

### 6. "Marca X como aplicado/descartado/contactado"
```bash
python3 estado/orquestador.py marcar vacantes "empresa::titulo" applied
```

### 7. "¿Qué tengo pendiente?" / "tareas" / "seguimientos"
```bash
python3 estado/orquestador.py tareas        # bandeja de entrada
python3 estado/orquestador.py seguimientos  # vencidos + bandeja
python3 estado/orquestador.py tarea-done t-YYYYMMDDHHMMSS-N
```

### 8. "Guía" / "cómo se usa esto"
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
- cliente contactado → categoría `clientes` (estado `contactado`)

Los scripts de `job-search` y `workana-search` ya deduplican solos
contra el historial; verifica su salida `---SKIPPED---`.
Cliente encolado → estado `en_proceso`; solo `contactado` (y su D+3)
tras el envío efectivo de `enviar-clientes`.

---

## Reglas de interacción

1. **Siempre confirma con el usuario antes de invadir su navegador**
   (linkedin-hidden-jobs, flutter-employers, prospectar-clientes y
   enviar-clientes abren chrome). Pregunta: "¿Abro el navegador para X?".
2. Para `cv-apply` y `linkedin-outreach`, pide autorización y datos
   mínimos que falten (URL de la vacante / perfil).
3. Mantén las respuestas concisas en el chat; los detalles van en los
   `.md` y en el informe diario.
4. Si una fuente falla (red, sesión), continúa con las demás y anótalo
   en el informe; nunca bloquees la ronda completa.

---

## Verificación rápida tras la ronda

```bash
python3 estado/tracker.py stats
python3 estado/orquestador.py estado
```