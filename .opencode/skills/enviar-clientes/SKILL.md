---
name: enviar-clientes
description: Envía uno por uno los mensajes de venta encolados por contactar-clientes, con validación del usuario en cada mensaje: muestra el mensaje completo, permite editarlo antes de enviar, envía por canal (email SMTP automático, WhatsApp Web vía navegador, LinkedIn semi), respeta el límite diario y la pausa entre envíos, y marca contactado + seguimiento D+3 solo tras el envío efectivo. No hay modo lote: siempre se aprueba el mensaje siguiente.
---

# Skill: enviar-clientes

Envía los mensajes que **`contactar-clientes` dejó en la cola**
(`estado/cola_envios.json`). No genera mensajes nuevos: solo envía lo
encolado.

**El flujo es UNO POR UNO:** se muestra el mensaje del siguiente lead en la
cola, el usuario lo valida (o lo modifica), se envía y recién ahí se pasa al
siguiente. No existe un modo "lote" que envíe todo de corrido.

Distinto de `linkedin-outreach` (empleo) y de `contactar-clientes`
(generación). Los servicios de IDUCDEV son **desarrollo web**, **apps
Flutter** y **diseño UI/UX**: nunca menciones n8n ni automatizaciones en
los mensajes.

## Disparo

- `"envía los pendientes"` / `"envía los mensajes"` / `"manda los de hoy"`
  → ronda uno por uno.
- Comando `/enviar` (default: ronda por-uno) · `/enviar solo email` ·
  `/enviar sin navegador`.
- `"¿qué hay en la cola?"` (solo listar, sin enviar).

## Referencias del proyecto (rutas relativas a la raíz)

- **Cola de envíos:** `estado/cola_envios.json`
- **CLI cola:** `python3 estado/cola_envios.py` (`add`, `pendientes`,
  `enviados-hoy`, `marcar`, `ver`, `editar`)
- **Email SMTP:** `python3 estado/enviar_email.py` (credenciales en `.env`)
- **DB de leads:** `resultados/clientes-potenciales/leads-db.json`
- **Orquestador:** `python3 estado/orquestador.py`
- **Config (límites):** `estado/config.py` → `ENVIO_MAX_DIA`,
  `ENVIO_PAUSA_WA_MIN/MAX`

## Workflow (ronda uno por uno)

### Fase 1: Leer cola y cupo

```bash
python3 estado/cola_envios.py pendientes
python3 estado/cola_envios.py enviados-hoy
```

- Sin pendientes → avisa y termina (`"No hay mensajes en cola. Genera uno
  con contactar-clientes primero."`).
- Cupo restante 0 → avisa: ya se llegó al límite diario
  (`ENVIO_MAX_DIA`, default 12). Los pendientes se quedan para mañana.

### Fase 2: Resumen de la cola y arranque de la ronda

Muestra la tabla de pendientes: **nombre | canal | destino | primera
línea del mensaje**. Avisa que la ronda es **uno por uno**: se mostrará y
validará cada mensaje antes de enviarlo.

Pide confirmación de empezar:

> Hay **N** mensajes en cola (X enviados hoy de M). ¿Empezamos la ronda?
> Si hay WhatsApp/LinkedIn en la cola → además: *"¿Abro el navegador?"*
> (autorización obligatoria, regla del repo).

**No envíes nada sin la confirmación de cada mensaje.** Si en cualquier
momento el usuario quiere parar, se termina la ronda y el resto queda
pendiente.

### Fase 3: Loop uno por uno (en orden de la cola)

Para **cada envío pendiente**, mientras quede cupo diario:

1. Re-chequea el cupo (`enviados-hoy`). Si es 0 → avisa y termina la ronda.
2. Muestra el **mensaje completo** del lead:
   ```bash
   python3 estado/cola_envios.py ver <id>
   ```
   (asunto + cuerpo + destino).
3. Presenta las opciones y espera la respuesta del usuario:

   "**¿Envío el mensaje a {nombre} por {canal}? (OK / modificar / saltar /
   parar)**"

   - **OK** → enviar por su canal (ver "Enviar por canal") → post-envío
     (Fase 4) → pasar al siguiente lead.
   - **Modificar** → aplicar los cambios y volver a mostrar (ver
     "Modificar un mensaje") → reconfirmar OK → enviar → post-envío →
     siguiente.
   - **Saltar** → **no marcar nada**: el lead queda `pendiente` para la
     próxima ronda. Pasar al siguiente.
   - **Parar** → terminar la ronda; el resto queda pendiente. Ir a Fase 5.

#### Modificar un mensaje

Si el usuario pide cambios, reescribe el cuerpo (conservando el
  estilo y la regla de no mencionar automatizaciones) en el `.md` original
  (`resultados/mensajes-clientes/{nombre}-{fecha}.md`, sección
  `## Mensaje`) y **sincroniza la cola**, de modo que el archivo y el envío
  queden idénticos:
  ```bash
  python3 estado/cola_envios.py editar <id> --cuerpo-file resultados/mensajes-clientes/{nombre}-{fecha}.md [--asunto "…"]
  ```
  O, para cambios puntuales sin tocar el `.md`:
  ```bash
  python3 estado/cola_envios.py editar <id> --cuerpo "nuevo texto completo…"
  ```
  (`--asunto`, `--destino` y `--nombre` también se pueden editar.)
- Tras editar, vuelve a mostrar con `ver <id>` para que el usuario confirme
  la versión final antes de enviar.
- No reescribas los mensajes entre sí para que se vean distintos: déjalos
  como se generaron salvo que el usuario pida un cambio concreto.

### Enviar por canal

#### Email → 100% automático (sin navegador)

```bash
python3 estado/enviar_email.py --id <id-envío>
```

- El script envía y **marca solo** el envío `enviado` (o `error` con
  motivo si falla SMTP).
- Si falla credenciales → indica crear `.env` desde `.env.example` con la
  contraseña de app de Gmail (`https://myaccount.google.com/apppasswords`).
- Validación puntual: `python3 estado/enviar_email.py --check`.

#### WhatsApp → automático vía WhatsApp Web (con navegador)

Requiere sesión iniciada en WhatsApp Web en el navegador del asistente
(primera vez: pedir escanear QR y **esperar a que el usuario diga que ya
logueó**).

1. Pausa previa (`sleep $((RANDOM % (MAX-MIN+1) + MIN))` con los valores
   de config; el primer envío de la ronda no necesita pausa larga).
2. Abrir/navegar a (URL prellena, teléfono sin `+` ni espacios):
   ```
   https://web.whatsapp.com/send?phone={telefono_limpio}&text={mensaje_urlencoded}
   ```
   (`chrome-devtools_navigate_page` o `new_page` si no hay pestaña WA).
3. Esperar a que cargue el chat (`chrome-devtools_wait_for`, timeout 15s).
4. Verificar que NO apareció el error de número no registrado
   ("El número de teléfono compartido... no está registrado en
   WhatsApp" / "no se puede usar"). Si aparece → **no enviar**: marcar
   `error` con motivo y continuar con el siguiente lead de la ronda.
5. Enviar: `chrome-devtools_press_key` `Enter` en el chat (o clic en el
   botón de enviar si Enter no funciona). Tomar snapshot/screenshot de
   verificación si hay duda (solo si el usuario lo pide o algo falla).
6. Post-envío (Fase 4).
7. Pausa aleatoria 15-35s antes del siguiente WhatsApp.

Si WhatsApp Web no está logueado → pausar la ronda, avisar al usuario que
loguee y reanudar cuando diga. **No** intentar automatizar el QR.

#### LinkedIn → semi (pega, NO envía)

1. Abrir el chat del perfil (URL del `destino` en la cola).
2. `chrome-devtools_type_text` / `fill` con el cuerpo del mensaje en el
   compositor.
3. **NO pulsar Enter ni clic de enviar.** Decirle al usuario:
   *"Mensaje pegado en el chat de {nombre}. Pulsa Tú Enter para enviarlo."*
4. Cuando el usuario confirme que lo envió → marcar `enviado` (Fase 4).
   Si prefiere, puede marcarlo él:
   `python3 estado/cola_envios.py marcar <id> enviado`.

### Fase 4: Post-envío por cada mensaje OK

```bash
# 1. Cola → enviado (si email, el script ya lo hace solo)
python3 estado/cola_envios.py marcar <id> enviado

# 2. Historial → contactado (crea tarea de seguimiento D+3)
python3 estado/orquestador.py marcar clientes "<lead_key>" contactado
```

3. Actualizar `resultados/clientes-potenciales/leads-db.json` del lead:

   ```json
   "status": "contacted",
   "fecha_contacto": "{YYYY-MM-DD}"
   ```

**Regla de oro:** `contactado` (y el D+3) **solo** tras envío efectivo.
Un email que falló o un WhatsApp a número inexistente queda en `error`
(reintentable) y el lead NO se marca contactado.

### Fase 5: Cierre de la ronda

Ya sea porque se agotó la cola, el cupo o porque el usuario paró:

```bash
python3 estado/orquestador.py registrar enviar-clientes resultados/mensajes-clientes/ --nuevas N --notas "email:N wa:N li:N errores:N saltados:N"
python3 estado/orquestador.py informe
```

Resumen final al usuario:

- enviados (por canal), errores (con motivo), **saltados** (quedan
  pendientes para la próxima ronda), pendientes que restan (fuera de cupo
  o por parar la ronda), cupo restante (`enviados-hoy`).

## Reglas de interacción

1. **Nunca enviar sin el OK de cada mensaje en particular.** Cada lead se
   valida individualmente (OK / modificar / saltar / parar). No hay lote.
2. **Navegador solo con autorización explícita** (WhatsApp Web /
   LinkedIn). Si no la hay, enviar solo los email y dejar el resto
   pendiente.
3. Respeta el límite diario y las pausas: queman el número/email si no.
4. Errores no cortan la ronda: se marcan `error` y se continúa con el
   siguiente lead.
5. **Saltar** deja el lead `pendiente`, sin marcar nada (ni error ni
   contactado): se retoma en la próxima ronda.
6. Mensajes tal cual los generó `contactar-clientes` por defecto: no los
   reescribas al enviar. Si el usuario pide un cambio, edita primero el
   `.md` y sincroniza la cola (`editar --cuerpo-file`) antes de enviar.
7. Nunca menciones n8n, automatizaciones ni flujos de trabajo en los
   mensajes.