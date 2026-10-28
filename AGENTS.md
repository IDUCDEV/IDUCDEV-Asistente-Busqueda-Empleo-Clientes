# AGENTS.md — Guía para agentes de IA en este repositorio

Repositorio del **Asistente IDUCDEV**: un agente delegado para buscar
empleo (Flutter/Dart remoto LATAM) y clientes (VE + empresas Flutter),
usando skills de openCode y un "cerebro" en `estado/`.

## Reglas de oro

1. **NUNCA hardcodear rutas.** La raíz se resuelve con `estado/config.py`
   (vía el marcador `.iducdev-root` o la env `IDUCDEV_PROJECT_DIR`). Usa
   rutas **relativas a la raíz** en comandos y docs; en Python, importa
   `from config import PROJECT_DIR, OUTPUT_DIRS, RESOURCES_DIR, ...`.
2. **CONSULTA SIEMPRE el centro de recursos.** Antes de ejecutar cualquier
   skill, lee `recursos/INDICE.md`: ahí está cada recurso de entrada y la
   salida esperada de cada skill. Los recursos de entrada (CV base, reglas
   ATS, guías) **NO se modifican**: los actualiza el humano.
3. **NUNCA repetir trabajo.** Todo lo visto queda en `estado/historial.json`
   (categorías + claves normalizadas). Consulta antes de mostrar, registra
   después.
4. **Entrada única:** la skill `asistente-empleo-clientes` es la puerta de
   entrada. La ronda CLI se delega con `estado/orquestador.py`.
5. **Toda salida de una skill va a `resultados/<carpeta-de-la-skill>/`.**
   Nunca sacar resultados a la raíz ni a `recursos/`.
6. **No commitear** a menos que el usuario lo pida explícitamente.

## Mapa del repo

```
recursos/             # CENTRO DE RECURSOS (entrada, lo mantiene el humano)
  INDICE.md           # mapa maestro: recursos + salidas (CONSULTAR SIEMPRE)
  cv/                 # base-isaac-urdaneta.md + CVs canónicos (ES/EN) + PDFs
  guias/              # cv-reglas-ats.md, linkedin.md
resultados/           # SALIDAS de las skills (se regeneran, ignoradas por git)
  vacantes/           #   ← job-search
  vacantes-web/       #   ← hidden-jobs-web (mobile.career, YC, X, site:boards.*)
  vacantes-ocultas/   #   ← linkedin-hidden-jobs
  clientes-potenciales/#  ← prospectar-clientes
  empresas-target/    #   ← flutter-employers
  mensajes-outreach/  #   ← linkedin-outreach (empleo)
  mensajes-clientes/  #   ← contactar-clientes (genera) → enviar-clientes (envía)
  cv/                 #   ← cv-apply (CV + carta + PDF)
  informes/           #   ← orquestador (resumen diario)
estado/
  config.py           # fuente única de rutas (IMPORTANTE)
  tracker.py          # helper historial: Historial, normalize_*, vacancy_key
  historial.json      # dedup central ("no repitas esto")
  tareas.json         # bandeja de entrada (acción + vencimiento)
  rondas.json         # bitácora de rondas (fases + conteos)
  cola_envios.json    # cola de envíos a clientes (contactar → enviar)
  cola_envios.py      # CLI cola: add, pendientes, enviados-hoy, marcar
  empresas_registry.json  # registro de empresas (versionado) ← flutter-employers
  empresas_cache.json     # cache de sondeo ATS (TTL 24 h, se regenera)
  enviar_email.py     # envío SMTP (Gmail app password, desde .env)
  orquestador.py      # CLI: ronda, registrar, estado, marcar, tareas, informe, reset
.env                  # credenciales SMTP + límites (NO commitear; ver .env.example)
.opencode/
  skills/             # las skills del asistente (proyecto-only)
  command/            # comandos /ronda /estado /nuevo /enviar
informes/  (ya no — ahora resultados/informes/)
```

## El cerebro (estado/)

- `orquestador.py ronda [--empleos|--clientes]` → corre `job_search.py` y
  `empresas_search.py`, anota las fases en `rondas.json` y regenera el
  informe diario en `resultados/informes/`. Las fases de navegador
  (hidden-jobs, prospectar, empresas) se registran con
  `orquestador.py registrar <fase> <archivo> --nuevas N`.
- **Búsqueda de empleo en 2 carriles:**
  - `job_search.py` (sin navegador, 13 fuentes agregadoras) →
    `resultados/vacantes/`. `--dry-run` no escribe nada.
  - `empresas_search.py` (tableros directos de diez ATS) →
    `resultados/empresas-target/`. Resuelve `ats`+`slug` leyendo la página de
    carreras del registro, probando el **host natural** de la empresa
    (`--host-directo`, activo: cubre Workable/Recruitee/BambooHR/Teamtailor/
    SmartRecruiters/Personio + Greenhouse/Ashby/Lever con el slug del dominio) y
    cachea 24 h (`empresas_cache.json`). Sondea en paralelo
    (`EMPRESAS_WORKERS`, un `Prober` por empresa), guarda cada 10 empresas y en
    `finally` (una ronda cortada no pierde el sondeo), emite solo el delta con
    `--nuevas` y **auto-encola** en `cola_aplicaciones.json` (`--no-encolar` lo
    desactiva). Un tablero que responde vacío se marca `tablero_vacio`, **nunca**
    "sin vacantes": suele ser slug equivocado. Workday **sí** tiene API pública
    (endpoint CXS, `POST`): el `<site>` del path va **sin locale** y el
    `<tenant>` no es el subdominio `wd<N>`. Los slugs a ciegas están
    **desactivados por defecto** (`--slugs-ciegos` los activa): miden ~0 % en
    LATAM y costaban ~10 peticiones por empresa.
  - `verificar_registro.py` **agranda el registro de forma verificada**: parte de
    `empresas_seed.json` y da de alta solo las empresas cuyo tablero devuelve
    ≥1 vacante real (nunca empresas inventadas con slugs supuestos). Corre en
    paralelo (`EMPRESAS_WORKERS`), es idempotente y además **repara** entradas
    con tablero sin resolver o placeholders antiguos. `--stats` dice qué falta.
    Un tablero vacío solo se descarta si el slug se adivinó (`Prober.resolution`):
    si lo dedujo la página de la empresa, 0 vacantes es "no hay vacantes".
    `--podar` marca `sin_dominio` y fusiona duplicados (nombre canónico,
    dominio o similitud en `tracker.names_similar`); `migrate_leads_db` usa esas
    mismas reglas para no volver a crear el duplicado que la poda acaba de
    fusionar.
  - `hidden-jobs-web` cubre lo no parseable (mobile.career, YC, X,
    `site:boards.*`) y da de alta empresas en `empresas_registry.json`.
- `orquestador.py estado` expone historial + bandeja + vencidos (pendientes
  y seguimientos). `seguimientos` crea tareas automáticas D+3 (outreach y
  clientes) y D+7 (aplicaciones) desde el historial.
- `marcar <cat> <key> <estado>` actualiza el historial y crea la tarea de
  seguimiento correspondiente.
- `reset [--yes]` vacía el estado para reempezar desde cero: historial,
  tareas y rondas. Pide confirmación salvo `--yes` (no toca `resultados/`).
- **Flujo de contacto a clientes (2 skills):** `contactar-clientes` genera
  el mensaje y lo **encola** (`cola_envios.py add`, lead `en_cola`);
  `enviar-clientes` envía **uno por uno** (muestra cada mensaje, lo valida
  con el usuario: ok/modificar/saltar/parar; email SMTP automático, WhatsApp
  Web con navegador, LinkedIn semi) y **solo tras envío efectivo** marca
  `orquestador.py marcar clientes <clave> contactado` (crea el D+3).
  Límite diario `ENVIO_MAX_DIA` (default 12) y pausa 15-35s entre WhatsApp.
- **Flujo de postulación a tableros ATS (1 skill):** las vacantes de
  `vacantes_empresa` se aplican con `cv-apply` **una a una**; el sondeo de
  `empresas_search.py` ya las deja en `cola_aplicaciones.json`. Al marcar
  `orquestador.py marcar vacantes_empresa "<empresa>::<titulo>" applied` se crea
  el seguimiento D+7 (`SEGUIMIENTO_DIAS["vacantes_empresa"]`).
  Los diez tableros soportados (Greenhouse, Ashby, Lever, Workday, Workable,
  Recruitee, Teamtailor, SmartRecruiters, BambooHR y Personio) usan
  **reCAPTCHA invisible** (v3, sin casilla) y renderizan el formulario por
  JavaScript: el envío **no** se puede automatizar por HTTP y lo hace el usuario
  en su navegador, pero **no hay desafío visible ni cupo semanal**.
- ⚠️ **Nunca automatizar ni esquivar una protección anti-bot.** Si un portal
  responde 403 + desafío (Cloudflare/Turnstile), se detiene la ronda y lo hace
  el usuario en su navegador. El scraping HTTP de páginas **públicas** sí es
  legítimo y es lo que usa todo el proyecto; lo que no se hace es automatizar
  la sesión autenticada ni evadir el desafío.

## Ciclo de vida del estado (historial.json)

`nuevo → revisado → en_proceso → aplicado/enviado → respuesta/descartado`

`tracker.py vencidos <dias>` lista items en `enviado/applied/contactado` sin
actualizar hace > N días (para no dejar contacts sin follow-up).

## Validación tras tocar código

```bash
python3 -m py_compile estado/*.py .opencode/skills/*/*.py
python3 -m unittest discover -s estado/tests
python3 estado/tracker.py stats
python3 estado/tracker.py normalizar --dry-run   # auditoría de claves de vacantes
python3 estado/orquestador.py estado
python3 estado/cola_envios.py pendientes
python3 estado/doctor.py
```

## Otras notas

- Abrir el navegador siempre con autorización previa del usuario
  (WhatsApp Web y LinkedIn de `enviar-clientes` incluidos).
- Credenciales SMTP y límites de envío viven en `.env` (gitignored);
  la plantilla es `.env.example`. Nunca mencionar las credenciales al
  usuario, ni commitear `.env`.
- Los scripts `job-search` y `empresas-search` resuelven la raíz caminando
  hacia arriba y volcando `estado/` en `sys.path`; no dependen de variables
  de entorno ni del cwd.
- El proyecto está pensado para renombrarse a una carpeta con la raíz limpia
  (`.iducdev-root` hace que funcione desde cualquier ubicación).