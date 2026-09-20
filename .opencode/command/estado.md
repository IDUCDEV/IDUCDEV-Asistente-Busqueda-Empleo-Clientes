# /estado — ¿Qué hay nuevo / pendiente?

Muestra el estado completo del asistente:

```bash
python3 estado/orquestador.py estado
```

Muestra: conteo por categoría (vacantes, empresas, clientes…), bandeja de
tareas pendientes y seguimientos vencidos. No ejecuta búsquedas nuevas.

Para la bandeja de tareas y seguimientos individuales:

```bash
python3 estado/orquestador.py tareas
python3 estado/orquestador.py seguimientos
python3 estado/orquestador.py tarea-done <id>
```