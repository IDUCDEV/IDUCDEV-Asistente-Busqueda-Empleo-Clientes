# AGENTS.md — Guía para agentes de IA en este repositorio

Repositorio del **Asistente IDUCDEV**: un agente delegado para buscar
empleo (Flutter/Dart remoto LATAM) y clientes (VE + empresas Flutter),
usando skills de openCode y un "cerebro" en `estado/`.

## Reglas de oro

1. **NUNCA hardcodear rutas.** La raíz se resuelve con `estado/config.py`
   (vía el marcador `.iducdev-root` o la env `IDUCDEV_PROJECT_DIR`). Usa
   rutas **relativas a la raíz** en comandos y docs; en Python, importa
   `from config import PROJECT_DIR, OUTPUT_DIRS, ...`.
2. **NUNCA repetir trabajo.** Todo lo visto queda en `estado/historial.json`
   (categorías + claves normalizadas). Consulta antes de mostrar, registra
   después.
3. **Entrada única:** la skill `asistente-empleo-clientes` es la puerta de
   entrada. La ronda CLI se delega con `estado/orquestador.py`.
4. **No commitear** a menos que el usuario lo pida explícitamente.

## Mapa del repo

```
estado/
  config.py          # fuente única de rutas (IMPORTANTE)
  tracker.py         # helper historial: Historial, normalize_*, vacancy_key
  historial.json     # dedup central ("no repitas esto")
  tareas.json        # bandeja de entrada (acción + vencimiento)
  rondas.json        # bitácora de rondas (fases + conteos)
  orquestador.py     # CLI: ronda, registrar, estado, marcar, tareas, informe
.opencode/
  skills/            # las 8 skills del asistente (proyecto-only)
  command/           # comandos /ronda /estado /nuevo
informes/            # resumenes diarios ({fecha}-resumen.md)
vacantes/            # output job-search
vacantes-workana/    # output workana-search
vacantes-ocultas/    # output linkedin-hidden-jobs
clientes-potenciales/# output prospectar-clientes (leads-db.json)
empresas-target/     # output flutter-employers (leads-db.json)
mensajes-outreach/   # output linkedin-outreach
```

## El cerebro (estado/)

- `orquestador.py ronda [--empleos|--clientes]` → corre `job_search.py` y
  `workana_search.py`, anota las fases en `rondas.json` y regenera el
  informe diario. Las fases de navegador (hidden-jobs, prospectar, empresas)
  se registran con `orquestador.py registrar <fase> <archivo> --nuevas N`.
- `orquestador.py estado` expone historial + bandeja + vencidos (pendientes
  y seguimientos). `seguimientos` crea tareas automáticas D+3 (outreach) y
  D+7 (aplicaciones) desde el historial.
- `marcar <cat> <key> <estado>` actualiza el historial y crea la tarea de
  seguimiento correspondiente.

## Ciclo de vida del estado (historial.json)

`nuevo → revisado → en_proceso → aplicado/enviado → respuesta/descartado`

`tracker.py vencidos <dias>` lista items en `enviado/applied/contactado` sin
actualizar hace > N días (para no dejar contacts sin follow-up).

## Validación tras tocar código

```bash
python3 -m py_compile estado/*.py .opencode/skills/*/*.py
python3 estado/tracker.py stats
python3 estado/orquestador.py estado
```

## Otras notas

- Abrir el navegador siempre con autorización previa del usuario.
- Los scripts `job-search` y `workana-search` resuelven la raíz caminando
  hacia arriba y volcando `estado/` en `sys.path`; no dependen de variables
  de entorno ni del cwd.
- El proyecto está pensado para renombrarse a una carpeta con la raíz limpia
  (`.iducdev-root` hace que funcione desde cualquier ubicación).