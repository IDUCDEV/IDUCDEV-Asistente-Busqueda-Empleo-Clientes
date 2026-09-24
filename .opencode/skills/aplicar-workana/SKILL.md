---
name: aplicar-workana
description: Genera propuestas de postulación personalizadas para proyectos de Workana (solo Flutter/Dart), filtra el listado de resultados/vacantes-workana/ + backlog del historial, redacta una propuesta freelancer por proyecto (entendimiento, solución en Flutter, plazo, presupuesto, CTA), guarda el .md en resultados/propuestas-workana/ y LO ENCOLA en estado/cola_envios.json (canal workana, destino = URL del proyecto) para que enviar-workana lo envíe uno por uno con validación del usuario. El estado applied (y seguimiento D+7) solo se marca tras el envío efectivo.
---

# Skill: aplicar-workana

Genera propuestas de **postulación en Workana** (paralelo de
`contactar-clientes`, pero para proyectos freelance). No envía: deja la
propuesta en cola para que `enviar-workana` la envíe **uno por uno** con
validación del usuario en el formulario de Workana.

Los servicios de IDUCDEV son **desarrollo web**, **apps Flutter** y
**diseño UI/UX**. Nunca menciones n8n, automatizaciones ni flujos de
trabajo en las propuestas.

## Disparo

- `"aplica a workana"` / `"prepara propuestas de workana"`
- `"genera propuestas para los proyectos flutter de workana"`
- `"encola las postulaciones de workana"`

## Referencias del proyecto (rutas relativas a la raíz)

- **Índice de recursos (consultar siempre):** `recursos/INDICE.md`
- **Listado de proyectos (entrada):** `resultados/vacantes-workana/{YYYY-MM-DD}.md`
- **Historial (dedup):** `estado/historial.json` — categoría `proyectos_workana`
  (campos planos: `key`, `titulo`, `url`, `author`, `budget`, `is_flutter`, `estado`)
- **CV base (firma y datos de Isaac):** `recursos/cv/base-isaac-urdaneta.md`
- **Cola de envíos (salida):** `estado/cola_envios.json` (CLI: `estado/cola_envios.py`, canal `workana`)
- **Output dir:** `resultados/propuestas-workana/`

## Workflow

### Fase 1: Leer índice e historial (regla de oro: no repetir)

1. Lee `recursos/INDICE.md`.
2. Consulta `estado/historial.json` (categoría `proyectos_workana`):

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "estado")
from tracker import Historial
h = Historial()
for it in h.data.get("proyectos_workana", []):
    print(it["key"], "|", it.get("estado"), "| flutter:", it.get("is_flutter"), "|", it.get("budget"))
EOF
```

- **No toques** proyectos con estado `applied`, `enviado`, `descartado`
  ni `en_proceso`.
- Si un proyecto ya tiene un envío `pendiente` en la cola
  (`python3 estado/cola_envios.py pendientes`), no lo dupliques.
- Trabaja solo sobre `is_flutter: true`.

### Fase 2: Seleccionar candidatos

Fuentes, en orden:

1. **Listado del día:** `resultados/vacantes-workana/{fecha}.md` (usa el más
   reciente de la carpeta). Los proyectos ✅ Flutter/Dart del listado.
2. **Backlog del historial:** proyectos con `is_flutter: true` y estado
   `nuevo` que aún no estén en el listado del día ni encolados.

Filtra candidatos con estas reglas:

- **Excluir siempre** (no son del stack IDUCDEV):
  - Keywords: `chatbot`, `automatización`, `automatizacion`, `bot de whatsapp`,
    `mensajes por whatsapp`, `low-code`, `filemaker`, `unity`, `realidad
    aumentada`, `esp32`, `iot`, `arduino`, `sistema embebido`, `motor`,
    `control de motores`, `scraping`, `ia`, `machine learning`.
  - Título o descripción que pidan un stack ajeno a Flutter/Dart (React
    Native, Swift, Java, Kotlin nativo, C++, Python) **a menos que el
    proyecto pida explícitamente Flutter/Dart o lo permita**.
- **Excluir por presupuesto** si el proyecto pide un MVP/producto completo y
  el presupuesto es irrisorio (p. ej. "Menos de USD 50", "USD 50 - 100").
  Un budget configurable mínimo razonable es **USD 500** o "por hora" con
  tarifa decente; si no, descártalo y anótalo.
- Aplica criterio de **viabilidad**: si el proyecto es de nicho muy ajena al
  stack (p. ej. solo Unity), descarta aunque tenga Flutter en las skills.

### Fase 3: Leer CV base

Lee `recursos/cv/base-isaac-urdaneta.md`. Extrae para las propuestas:
nombre, firma, portafolio (`www.iducdev.org`), LinkedIn, y los logros con
números (ej. 40% mejora SSR, 98% accesibilidad Lighthouse, 50% menos tiempo
de configuración, 3+ apps en producción) para usarlos como prueba social.

### Fase 4: Elegir a quién proponer

Presenta la lista final de candidatos (título, cliente, presupuesto, URL y
mirada rápida de alineación) y **pregunta la confirmación del usuario** antes
de generar: filtrar solo Flutter/Dart, excluir automatizaciones, mínimo de
presupuesto. Es la puerta de validación humana de `aplicar-workana`.

Si el usuario quiere simplificar (p. ej. "solo los de hoy"), respeta su
decisión. Puede decir "todos" explícitamente.

### Fase 5: Generar propuesta por proyecto

Para **cada** proyecto confirmado, redacta una **propuesta de postulación de
Workana** (máx. 120-150 palabras; Workana valora concisión). Estructura en
párrafos cortos:

1. **Saludo al cliente** por su nombre.
2. **Entendimiento del proyecto** en 1-2 líneas (releer la descripción),
   demostrando que leíste la publicación.
3. **Cómo lo resolvería** con Flutter/Dart (Clean Architecture, BLoC,
   Supabase si aplica, estado offline, etc.), anclado a las necesidades
   concretas del proyecto.
4. **Prueba social** (1 logro numerado del CV base o proyecto publicado).
5. **Plazo estimado y presupuesto** acorde al presupuesto publicado por el
   cliente (no inventes cifras fijas: di que el plazo/costo se afinan en la
   primera llamada según alcance exacto; si el proyecto pide un rango,
   respétalo).
6. **CTA:** ofrecer una llamada/videollamada breve para revisar el detalle.
7. **Firma:** Isaac Urdaneta — IDUCDEV | www.iducdev.org | LinkedIn.

Ejemplo de esqueleto:

> Hola [cliente]:
>
> Revisé tu proyecto de [descripción corta]. [Detalle que demuestre que lo
> leíste].
>
> Lo desarrollaría en Flutter con Clean Architecture y BLoC, [cómo
> resuelves el punto clave del proyecto]. Si necesitas [datos offline/
> notificaciones/agendamiento], ya lo he resuelto en proyectos similares.
>
> [1 logro numerado del CV base, ej. "en proyectos anteriores reduje un 40%
> el tiempo de carga"].
>
> El plazo y el costo se afinan en la primera llamada según el alcance
> exacto. ¿Podemos tener una videollamada breve para revisarlo?
>
> — Isaac Urdaneta · IDUCDEV
> www.iducdev.org

Adapta el esqueleto a cada proyecto: el hook del punto 2 **siempre** debe
referirse a la descripción real de esa publicación.

### Fase 6: Guardar, encolar y registrar

1. Guarda **un .md por proyecto**:

   ```
   resultados/propuestas-workana/{key-proyecto}-{YYYY-MM-DD}.md
   ```

   `key-proyecto` = el slug/key del proyecto (el mismo del historial).

   ```markdown
   # Propuesta Workana — {título del proyecto}
   - **Cliente:** {author}
   - **Presupuesto publicado:** {budget}
   - **Fecha:** {YYYY-MM-DD}
   - **URL:** {url}

   ---

   ## Mensaje

   [la propuesta completa]

   ---

   ## Notas
   - Fuente: listado del día | backlog
   - Alineación: ...
   - Siguiente paso: decir "envía las propuestas de workana"
   ```

   (La sección `## Mensaje` es contigo vía la extracción de
   `cola_envios.py`, igual que `contactar-clientes`.)

2. **Encola el envío** (canal `workana`, destino = URL del proyecto):

   ```bash
   python3 estado/cola_envios.py add \
     --key "<key-proyecto>" \
     --nombre "<título corto del proyecto>" \
     --canal workana \
     --destino "<url del proyecto>" \
     --mensaje-path "resultados/propuestas-workana/{key}-{fecha}.md"
   ```

   - Dedup: si el proyecto ya estaba `pendiente`, no se duplica.
   - El `--destino` es el que `enviar-workana` abrirá en el navegador.

3. Marca el proyecto en el historial como `en_proceso` (dedup sin disparar
   seguimiento):

   ```bash
   python3 - <<'EOF'
   import sys
   sys.path.insert(0, "estado")
   from tracker import Historial
   h = Historial()
   h.set_state("proyectos_workana", "<key-proyecto>", "en_proceso")
   EOF
   ```

   **NO marques `applied` todavía:** eso ocurre solo tras el envío efectivo
   (lo hace `enviar-workana`), para que el D+7 cuente desde la postulación
   real.

4. Muestra al usuario el resumen (N propuestas generadas, M encoladas, K
   descartadas con motivo) y dile que el siguiente paso es:

   > **"envía las propuestas de workana"** → `enviar-workana` arranca la
   > ronda uno por uno: muestra cada propuesta, la validas y la pega en el
   > formulario de postulación de Workana (tú pulsas enviar).

## Reglas de interacción

- Esta skill **genera y encola**; **no envía**. El envío es de
  `enviar-workana`.
- No abras el navegador en esta skill.
- Solo proyectos `is_flutter: true`. Excluye siempre automatizaciones /
  chatbot / low-code / filemaker / unity / IoT (regla IDUCDEV).
- No inventes presupuestos ni plazos duros; di que se afinan en la primera
  llamada.
- Nunca menciones n8n, automatizaciones ni flujos de trabajo en las
  propuestas.
- No reabra ni modifiques propuestas de proyectos que ya están `applied`,
  `enviado` o `descartado`: respeta el historial.