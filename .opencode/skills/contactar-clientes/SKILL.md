---
name: contactar-clientes
description: Genera un mensaje de venta personalizado para contactar a un lead de clientes (resultado de prospectar-clientes). Lee el lead desde resultados/clientes-potenciales/leads-db.json o datos manuales, adapta el mensaje al canal (whatsapp/email/linkedin) y tono, lo guarda en resultados/mensajes-clientes/ y LO ENCOLA en estado/cola_envios.json para que enviar-clientes lo envíe uno por uno (validación del usuario en cada mensaje). El estado contactado (y seguimiento D+3) solo se marca tras el envío efectivo.
---

# Skill: contactar-clientes

Genera mensajes personalizados para **contactar clientes potenciales**
(distinto de `linkedin-outreach`, que es solo para búsqueda de empleo).

En este proyecto no hay automatizaciones: los servicios de IDUCDEV son
**desarrollo web**, **apps Flutter** y **diseño UI/UX**. Nunca menciones
n8n, automatizaciones ni flujos de trabajo en el mensaje.

## Disparo

El usuario te pide algo como:

- `"contactar {nombre-del-lead}"`
- `"mensaje para {nombre-del-lead}"`
- `"outreach para cliente {nombre}"`
- `"prepara el contacto de {nombre}"`

## Referencias del proyecto (rutas relativas a la raíz)

- **Indice de recursos (consultar siempre):** `recursos/INDICE.md`
- **DB de leads (entrada):** `resultados/clientes-potenciales/leads-db.json`
- **CV base (firma y datos de Isaac):** `recursos/cv/base-isaac-urdaneta.md`
- **Cola de envíos (salida):** `estado/cola_envios.json` (CLI: `estado/cola_envios.py`)
- **Output dir:** `resultados/mensajes-clientes/`

## Workflow

### Fase 1: Leer índice e historial (regla de oro: no repetir)

1. Lee `recursos/INDICE.md`.
2. Consulta `estado/historial.json` (categoría `clientes`) con el helper
   `estado/tracker.py` para saber la clave y el estado del lead:

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "estado")
from tracker import Historial, domain_key
h = Historial()
for it in h.data.get("clientes", []):
    print(it["key"], "|", it.get("estado"))
EOF
```

- Si el lead ya está `contactado`/`enviado` y tiene un mensaje generado,
  avísale al usuario y ofrécele regenerarlo (no lo regeneres sin preguntar).
- Si su estado es `en_proceso` y ya hay algo pendiente en
  `python3 estado/cola_envios.py pendientes` para ese lead, avisa que ya
  está en cola (no lo dupliques).

### Fase 2: Localizar el lead

Busca el lead por **nombre** en `resultados/clientes-potenciales/leads-db.json`
(normalizando: minúsculas, sin tildes, sin espacios extra). Campos útiles:
`name`, `phone`, `website`, `address`, `industry`, `score`, `service`,
`pain_points`, `icebreaker`, `channel`, `status`.

- Si lo encuentras → usa sus datos tal cual.
- Si no existe en la DB → pide al usuario los datos mínimos: nombre del
  negocio, rubro, canal de contacto (whatsapp/email/linkedin) y una nota de
  contexto. Genera el mensaje igualmente.

### Fase 3: Leer CV base

Lee `recursos/cv/base-isaac-urdaneta.md` para obtener: nombre, contacto,
email freelance, LinkedIn/GitHub, portafolio y propuesta de valor.
Usa esos datos en la firma y en el mensaje.

### Fase 4: Elegir canal y tono

**Canal** (en orden de prioridad):
1. El `channel` del lead en la DB (si existe).
2. Si hay `phone` y no hay canal → `whatsapp`.
3. Si no hay teléfono → `email` (si hay website/mail) o `linkedin`.

Pregunta el tono solo si el usuario no lo especificó:

| Tono | Cuándo usarlo |
|---|---|
| **Directo y natural** (recomendado) | La mayoría de los casos. Profesional pero cercano. |
| **Profesional formal** | Clínicas, hoteles, empresas consolidadas, cargos senior. |
| **Casual/amistoso** | Gimnasios, barberías, startups, negocios jóvenes. |

### Fase 5: Generar el mensaje

Usa estos templates según canal y tono, interpolando los datos del lead
(`icebreaker`, `pain_points`, `service`, industry) y de Isaac del CV base.
El mensaje siempre debe: abrir con un **hook personalizado** (que demuestre
que viste su negocio), señalar el **pain point**, ofrecer un **servicio
concreto** (web / apps Flutter / UI/UX), cerrar con una **CTA** clara.

#### WhatsApp

**Directo y natural (recomendado):**

> Hola [nombre], le escribo de IDUCDEV.
>
> [Hook con su negocio: ej. "He visto su página web y me llamó la atención
> que [detalle real]."]
>
> [Pain point detectado: ej. "Por lo que vi, [frustración que tendrían]."]
>
> Yo desarrollo [web/apps/UI] — por ejemplo [logro/referencia]. ¿Le interesa
> que le cuente cómo lo haríamos en su caso? Puedo mostrarle una propuesta
> breve sin compromiso.
>
> — Isaac Urdaneta | IDUCDEV
> [portafolio]

**Profesional formal:**

> Estimado/a [nombre]:
>
> Mi nombre es Isaac Urdaneta de IDUCDEV. [Hook + contexto: lo que hizo que
> su negocio apareciera en mi radar].
>
> [Pain point + como lo resolvería con servicio concreto].
>
> Quedo a disposición para agendar una breve conversación cuando le
> convenga. Saludos cordiales.
>
> — Isaac Urdaneta | IDUCDEV | [portafolio] | [email]

**Casual/amistoso:**

> ¡Hola [nombre]!
>
> Vi [su negocio/web/perfil] y la verdad me gustó [detalle]. [Hook].
>
> [Pain point + oferta]. ¿Qué tal si lo vemos un momento? Le paso ideas sin
> costo.
>
> — Isaac, IDUCDEV
> [portafolio]

#### Email

**Asunto:** [una línea específica, ej. "Rediseño de su web para citas online"]

**Directo y natural:**

> Hola [nombre]:
>
> [Hook personalizado, 1-2 líneas sobre su negocio.web].
>
> [Pain point en 1 línea]. En IDUCDEV desarrollamos [servicio]. [Social
> proof breve: portafolio / apps publicadas].
>
> Si le interesa, con gusto comparto una propuesta breve. ¿Podemos
> conversar esta semana?
>
> Saludos,
> Isaac Urdaneta | IDUCDEV
> [portafolio] | [linkedin]

**Profesional formal:** misma estructura pero con "Estimado/a", sin
contracciones y con cierre "Saludos cordiales".

#### LinkedIn

**Directo y natural:**

> Hola [nombre]:
>
> Gracias por la conexión. Soy Isaac Urdaneta, desarrollo web y apps
> (Flutter) en IDUCDEV. [Hook con su negocio].
>
> [Pain point + oferta]. Si le sirve, puedo enviarle una propuesta breve.
> ¡Gracias!

**Casual:**
> ¡Hola [nombre]! Vi [su negocio] y quería comentarle [hook]. Trabajo en
> IDUCDEV haciendo [servicio]; si necesitan [pain point], con gusto les
> doy una mano.

### Fase 6: Guardar, encolar y mostrar

1. Guarda el mensaje en:

   ```
   resultados/mensajes-clientes/{nombre-normalizado}-{YYYY-MM-DD}.md
   ```

   Donde `nombre-normalizado` es el nombre del negocio en lowercase con
   guiones (ej: `clinica-ccct`).

   Estructura del archivo:

   ```markdown
   # Mensaje de contacto — {nombre del negocio}
   - **Cliente:** {nombre} | {industry}
   - **Canal:** whatsapp/email/linkedin
   - **Tono:** ...
   - **Fecha:** {YYYY-MM-DD}
   - **Lead score:** {score} | **Servicio sugerido:** {web_app/flutter_app/multiple}

   ---

   ## Mensaje (listo para copiar)

   [el mensaje completo]

   ---

   ## Notas
   - Pain points: ...
   - Contexto del lead: ...
   - Siguiente paso: decir "envía los pendientes" (o enviarlo a mano y marcar contactado)
   ```

2. **Encola el envío** con `estado/cola_envios.py` (el envío lo hará la
   skill `enviar-clientes` uno por uno, con validación del usuario en cada
   mensaje y límite diario):

   ```bash
   python3 estado/cola_envios.py add \
     --key "<clave-del-lead>" \
     --nombre "<nombre del negocio>" \
     --canal whatsapp|email|linkedin \
     --destino "<teléfono | email | url linkedin>" \
     --mensaje-path "resultados/mensajes-clientes/{nombre}-{fecha}.md" \
     [--asunto "<asunto del email>"]
   ```

   - `--destino`: `phone` del lead (whatsapp), `email`/website-derived
     (email) o URL del perfil (linkedin). Si el lead no tiene destino
     válido para su canal, avísalo y deja solo el `.md` (envío manual).
   - El `--asunto` es obligatorio solo para canal `email`.
   - Dedup: si el lead ya estaba `pendiente` en la cola, no se duplica.

3. Actualiza el lead en `resultados/clientes-potenciales/leads-db.json`:

   ```json
   "status": "en_cola",
   "mensaje": "resultados/mensajes-clientes/{nombre}-{fecha}.md"
   ```

   **NO marques todavía `contacted` ni `contactado` en el historial:** eso
   ocurre solo tras el envío efectivo (lo hace `enviar-clientes`), para que
   el seguimiento D+3 cuente desde que el lead realmente recibió el mensaje.

4. Registra/asegura la clave en el historial en estado `en_proceso`
   (dedup sin disparar seguimiento):

   ```bash
   python3 - <<'EOF'
   import sys
   sys.path.insert(0, "estado")
   from tracker import Historial, domain_key
   h = Historial()
   clave = domain_key("<website>") or "<nombre normalizado>"
   if not h.is_known("clientes", clave):
       h.add("clientes", clave, meta={"nombre": "...", "rubro": "...", "web": ...})
   h.set_state("clientes", clave, "en_proceso")
   EOF
   ```

5. Muestra el mensaje al usuario y dile que el siguiente paso es:

   > **"envía los pendientes"** (o `/enviar`) → `enviar-clientes` arranca
   > la ronda uno por uno: muestra cada mensaje, lo validas y lo envía por
   > WhatsApp/email/LinkedIn con límite diario. También puede
   > copiarlo/pegarlo a mano; si lo hace a mano, ahí sí marca `contactado`:
   >
   > ```bash
   > python3 estado/orquestador.py marcar clientes "<clave>" contactado
   > ```

## Reglas de interacción

- Esta skill **genera y encola**; **no envía**. El envío es de
  `enviar-clientes` (validación del usuario en cada mensaje) o manual por
  el usuario.
- No abras el navegador en esta skill: el mensaje queda en cola o en el
  `.md` para envío manual.
- Si el lead ya está `contactado`/`enviado` y tiene un mensaje generado,
  avísale al usuario y ofrécele regenerarlo (no lo regeneres sin preguntar).
- Mantén el mensaje conciso; los detalles van en el `.md`.
- Nunca menciones n8n, automatizaciones ni flujos de trabajo.