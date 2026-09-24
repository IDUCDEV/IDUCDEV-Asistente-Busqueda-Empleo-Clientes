---
name: enviar-workana
description: Envía uno por uno las propuestas de postulación encoladas por aplicar-workana (canal workana), con validación del usuario en cada propuesta: muestra la propuesta completa, permite editarla antes de enviar, abre la URL del proyecto en Workana, pega título + propuesta en el formulario de postulación y el usuario pulsa enviar (semi), respeta el límite diario compartido, y marca applied + seguimiento D+7 solo tras el envío efectivo (orquestador.py marcar proyectos_workana <key> applied). No hay modo lote: siempre se aprueba la propuesta siguiente.
---

# Skill: enviar-workana

Envía las propuestas de postulación que **`aplicar-workana`** dejó en la cola
(`estado/cola_envios.json`, canal `workana`). No genera propuestas nuevas:
solo envía lo encolado.

**El flujo es UNO POR UNO:** se muestra la propuesta del siguiente proyecto,
el usuario la valida (o la modifica), se pega en el formulario de postulación
de Workana y **el usuario pulsa enviar**. No existe modo lote.

Distinto de `enviar-clientes` (clientes por WhatsApp/email/LinkedIn). Solo
toca envíos de canal `workana`. Los servicios de IDUCDEV son **desarrollo
web**, **apps Flutter** y **diseño UI/UX**: nunca menciones n8n ni
automatizaciones en las propuestas.

## Disparo

- `"envía las propuestas de workana"` / `"envía los pendientes de workana"`
  / `"manda las postulaciones"`.
- `"¿qué hay en la cola?"` (solo listar, sin enviar).

## Referencias del proyecto (rutas relativas a la raíz)

- **Cola de envíos:** `estado/cola_envios.json`
- **CLI cola:** `python3 estado/cola_envios.py` (`add`, `pendientes`,
  `enviados-hoy`, `marcar`, `ver`, `editar`)
- **Orquestador:** `python3 estado/orquestador.py`
- **Config (límites):** `estado/config.py` → `ENVIO_MAX_DIA`,
  `SEGUIMIENTO_DIAS["proyectos_workana"]` = 7
- **Historial (dedup):** `estado/historial.json` → categoría `proyectos_workana`

## Workflow (ronda uno por uno)

### Fase 0: Autorización de navegador

Workana se envía **en la web** (`workana.com`), así que esta ronda **siempre
necesita navegador**. Pide autorización explícita al usuario antes de abrir
Workana. La **primera vez** (o si la sesión caducó):

1. Abre `https://www.workana.com` en el navegador del asistente.
2. Si no está logueado → pide al usuario que **inicie sesión él mismo**
   (login de Workana, a veces con Google) y **espera a que diga que ya
   logueó**. No intentes automatizar el login ni las credenciales.

### Fase 1: Leer cola y cupo (solo canal `workana`)

```bash
python3 estado/cola_envios.py pendientes
python3 estado/cola_envios.py enviados-hoy
```

- Filtra la tabla a los envíos de **canal `workana`**.
- Sin pendientes de workana → avisa y termina: `"No hay propuestas en cola.
  Genera una con aplicar-workana primero."`
- Cupo restante 0 → avisa: se llegó al límite diario (`ENVIO_MAX_DIA`,
  default 12; compartido con clientes). Los pendientes se quedan para mañana.

### Fase 2: Resumen de la cola y arranque de la ronda

Muestra la tabla de pendientes de workana: **proyecto | destiño | primera
línea de la propuesta**. Pide confirmación de empezar:

> Hay **N** propuestas de workana en cola (X enviados hoy de M).
> ¿Empezamos la ronda? *(Requiere navegador con sesión en workana.com: ¿abro
> Workana?)*

**No envíes nada sin confirmación y sin usuario logueado.** Si en cualquier
momento el usuario quiere parar, se termina la ronda y el resto queda
pendiente.

### Fase 3: Loop uno por uno (en orden de la cola, solo canal workana)

Para **cada propuesta pendiente de workana**, mientras quede cupo diario:

1. Re-chequea el cupo (`enviados-hoy`). Si es 0 → avisa y termina la ronda.
2. Muestra la **propuesta completa**:
   ```bash
   python3 estado/cola_envios.py ver <id>
   ```
3. Presenta las opciones y espera respuesta del usuario:

   "**¿Envío la propuesta al proyecto {nombre} en Workana? (OK / modificar /
   saltar / parar)**"

   - **OK** → enviar por canal workana (ver "Enviar por canal workana") →
     post-envío (Fase 4) → siguiente proyecto.
   - **Modificar** → aplicar los cambios y volver a mostrar (ver "Modificar
     una propuesta") → reconfirmar OK → enviar → post-envío → siguiente.
   - **Saltar** → **no marcar nada**: queda `pendiente` para la próxima
     ronda. Pasar al siguiente.
   - **Parar** → terminar la ronda; el resto queda pendiente. Ir a Fase 5.

#### Modificar una propuesta

Si el usuario pide cambios, reescribe el cuerpo (conservando el estilo y la
regla de no mencionar automatizaciones) en el `.md` original
(`resultados/propuestas-workana/{key}-{fecha}.md`, sección `## Mensaje`) y
**sincroniza la cola**, de modo que el archivo y el envío queden idénticos:

```bash
python3 estado/cola_envios.py editar <id> --cuerpo-file resultados/propuestas-workana/{key}-{fecha}.md
```

O, para cambios puntuales sin tocar el `.md`:

```bash
python3 estado/cola_envios.py editar <id> --cuerpo "nuevo texto completo…"
```

Tras editar, vuelve a mostrar con `ver <id>` para que el usuario confirme la
versión final antes de enviar.

### Enviar por canal workana (semi — pega, NO envía)

1. Abre la URL del proyecto (`destino` de la cola) en el navegador:
   `chrome-devtools_navigate_page` o `new_page`.
2. Ubica el botón de postular / formulario de propuesta de Workana
   (normalmente un botón "Postular" / "Apply" y luego un formulario con
   campos de **título/subject** y **descripción/propuesta**). Toma un
   `snapshot` si el botón no es evidente.
3. Pega el **título** (una línea corta con la esencia de la propuesta, ej.
   "Flutter Engineer — desarrollo de {servicio} con entrega por fases") y la
   **propuesta completa** (el `cuerpo` de la cola) en el campo de descripción.
   Usa `chrome-devtools_fill` / `type_text` / `fill_form`.
4. **NO pulsar enviar.** Decirle al usuario:
   *"Propuesta pegada en el formulario de {proyecto}. Completa los campos
   restantes (presupuesto/fecha si Workana los pide) y pulsa Tú el botón
   para postularte."*
5. Cuando el usuario confirme que la envió → marcar `enviado` (Fase 4).
   Si prefiere, puede marcarlo él: `python3 estado/cola_envios.py marcar
   <id> enviado`.

### Fase 4: Post-envío por cada propuesta OK

```bash
# 1. Cola → enviado
python3 estado/cola_envios.py marcar <id> enviado

# 2. Historial → applied (crea tarea de seguimiento D+7)
python3 estado/orquestador.py marcar proyectos_workana "<key-proyecto>" applied
```

**Regla de oro:** `applied` (y el D+7) **solo** tras postulación efectiva en
Workana. Si el usuario por cualquier motivo no llegó a enviar (botón no
encontrado, proyecto cerrado), deja el envío `pendiente` o márcalo `error`
con motivo, y **NO** marques `applied`.

### Fase 5: Cierre de la ronda

```bash
python3 estado/orquestador.py registrar enviar-workana resultados/propuestas-workana/ --nuevas N --notas "workana:N errores:N saltados:N"
python3 estado/orquestador.py informe
```

Resumen final al usuario:

- propuestas enviadas, errores (con motivo), **saltadas** (quedan pendientes
  para la próxima ronda), pendientes restantes (fuera de cupo o por parar),
  cupo restante (`enviados-hoy`).

## Reglas de interacción

1. **Nunca enviar sin el OK de cada propuesta en particular.** Uno por uno.
2. **Navegador solo con autorización explícita** y sesión `workana.com`
   iniciada por el usuario. Si Workana pide login, espera a que loguee.
3. Respeta el límite diario compartido (`ENVIO_MAX_DIA`): Workana también
   limita postulaciones diarias.
4. Errores no cortan la ronda: se marcan `error` (o `pendiente`) y se sigue
   con la siguiente propuesta.
5. **Saltar** deja el proyecto `pendiente`, sin marcar nada: se retoma en la
   próxima ronda.
6. Propuestas tal cual las generó `aplicar-workana` por defecto: no las
   reescribas al enviar. Si el usuario pide un cambio, edita primero el `.md`
   y sincroniza la cola (`editar --cuerpo-file`) antes de enviar.
7. Nunca menciones n8n, automatizaciones ni flujos de trabajo en las
   propuestas.
8. No postular a proyectos cuyo presupuesto fue excluido por `aplicar-workana`
   (regla de la skill de generación).