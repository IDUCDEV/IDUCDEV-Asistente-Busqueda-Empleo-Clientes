# /ronda — Ejecuta la ronda de hoy (empleos + clientes)

Carga la skill `asistente-empleo-clientes` y ejecuta la ronda tal como la
define, SIN repetir nada (consulta `estado/historial.json`).

Flujo:

1. Sin navegador → scripts de búsqueda:
   ```bash
   python3 estado/orquestador.py ronda --empleos
   ```
2. Con navegador (solo si el usuario autoriza) → `linkedin-hidden-jobs`,
   `prospectar-clientes`, `flutter-employers`. Tras cada fase:
   ```bash
   python3 estado/orquestador.py registrar <fase> <archivo> --nuevas N --omitidas M
   ```
3. Consolidar informe:
   ```bash
   python3 estado/orquestador.py informe
   ```

Al terminar muestra el resumen y cuántas cosas nuevas vs omitidas hubo.