#!/usr/bin/env python3
"""config.py — Fuente única de rutas y configuración del proyecto IDUCDEV.

Ningún script ni skill debe hardcodear la ruta absoluta del proyecto.
Aquí se resuelve la raíz con esta prioridad:

1. Env var ``IDUCDEV_PROJECT_DIR`` (override explícito, p. ej. en otros SO).
2. El marcador ``.iducdev-root`` en la raíz del proyecto (caminando hacia arriba).
3. La presencia de la carpeta ``estado/``.

Esto hace que el proyecto funcione igual aunque cambie de carpeta o máquina.

Uso desde cualquier script (dentro o fuera de la raíz):

    import sys, os
    sys.path.insert(0, <ruta a la carpeta estado resuelta>)
    from config import PROJECT_DIR, OUTPUT_DIRS, HISTORIAL_PATH
"""

import os

_MARKER = ".iducdev-root"


def project_root(start=None):
    env = os.environ.get("IDUCDEV_PROJECT_DIR")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    start = os.path.abspath(start or __file__)
    d = os.path.dirname(start) if os.path.isfile(start) else start
    for _ in range(8):
        if os.path.exists(os.path.join(d, _MARKER)) or os.path.isdir(os.path.join(d, "estado")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return start


def skills_bootstrap(paths_dirs):
    """Inserta en sys.path las carpetas `estado` y `tracker` dadas, devolviendo PROJECT_DIR.

    `paths_dirs` es una lista de directorios candidatos a contener `estado/`.
    Pensado para scripts dentro de `.opencode/skills/<skill>/`.
    """
    import sys  # noqa: PLC0415
    root = None
    for d in paths_dirs:
        r = project_root(d)
        if os.path.isdir(os.path.join(r, "estado")):
            root = r
            break
    if root is None:
        env = os.environ.get("IDUCDEV_PROJECT_DIR")
        root = os.path.abspath(env) if env else None
    if root is None:
        sys.exit("No se localizó el proyecto IDUCDEV. Define IDUCDEV_PROJECT_DIR.")
    sys.path.insert(0, os.path.join(root, "estado"))
    return root


PROJECT_DIR = project_root()
ESTADO_DIR = os.path.join(PROJECT_DIR, "estado")
SKILLS_DIR = os.path.join(PROJECT_DIR, ".opencode", "skills")
RESOURCES_DIR = os.path.join(PROJECT_DIR, "recursos")
RESULTADOS_DIR = os.path.join(PROJECT_DIR, "resultados")


def _load_dotenv(path):
    """Carga un .env simple (KEY=VALUE) sin dependencias. No pisa env existentes."""
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except OSError:
        pass


_load_dotenv(os.path.join(PROJECT_DIR, ".env"))

HISTORIAL_PATH = os.path.join(ESTADO_DIR, "historial.json")
TAREAS_PATH = os.path.join(ESTADO_DIR, "tareas.json")
RONDAS_PATH = os.path.join(ESTADO_DIR, "rondas.json")
COLA_ENVIOS_PATH = os.path.join(ESTADO_DIR, "cola_envios.json")

# Envío de mensajes a clientes (cola + rate limit)
ENVIO_MAX_DIA = int(os.environ.get("ENVIO_MAX_DIA", "12"))
ENVIO_PAUSA_WA_MIN = int(os.environ.get("ENVIO_PAUSA_WA_MIN", "15"))
ENVIO_PAUSA_WA_MAX = int(os.environ.get("ENVIO_PAUSA_WA_MAX", "35"))
EMAIL_USER = os.environ.get("EMAIL_USER", "")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "")

OUTPUT_DIRS = {
    "vacantes": os.path.join(RESULTADOS_DIR, "vacantes"),
    "vacantes-workana": os.path.join(RESULTADOS_DIR, "vacantes-workana"),
    "vacantes-ocultas": os.path.join(RESULTADOS_DIR, "vacantes-ocultas"),
    "clientes-potenciales": os.path.join(RESULTADOS_DIR, "clientes-potenciales"),
    "empresas-target": os.path.join(RESULTADOS_DIR, "empresas-target"),
    "mensajes-outreach": os.path.join(RESULTADOS_DIR, "mensajes-outreach"),
    "mensajes-clientes": os.path.join(RESULTADOS_DIR, "mensajes-clientes"),
    "propuestas-workana": os.path.join(RESULTADOS_DIR, "propuestas-workana"),
    "cv": os.path.join(RESULTADOS_DIR, "cv"),
    "informes": os.path.join(RESULTADOS_DIR, "informes"),
}

SKILL_SCRIPTS = {
    "job-search": os.path.join(SKILLS_DIR, "job-search", "job_search.py"),
    "workana-search": os.path.join(SKILLS_DIR, "workana-search", "workana_search.py"),
}

# Seguimientos automáticos: cuántos días después se crea una tarea de revisión.
SEGUIMIENTO_DIAS = {
    "outreach": 3,      # contacto enviado → revisar respuesta en 3 días
    "clientes": 3,      # lead contactado → revisar respuesta en 3 días
    "vacantes": 7,      # aplicación enviada → revisar status en 7 días
    "proyectos_workana": 7,
}


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


if __name__ == "__main__":
    print(f"PROJECT_DIR      : {PROJECT_DIR}")
    print(f"ESTADO_DIR       : {ESTADO_DIR}")
    print(f"SKILLS_DIR       : {SKILLS_DIR}")
    print(f"RESOURCES_DIR    : {RESOURCES_DIR}")
    print(f"RESULTADOS_DIR   : {RESULTADOS_DIR}")
    print(f"HISTORIAL_PATH   : {HISTORIAL_PATH}")
    print(f"TAREAS_PATH      : {TAREAS_PATH}")
    print(f"RONDAS_PATH      : {RONDAS_PATH}")
    for key, path in OUTPUT_DIRS.items():
        print(f"OUTPUT {key:<18}: {path}")