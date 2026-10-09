#!/usr/bin/env python3
"""doctor.py — Diagnóstico de salud del asistente IDUCDEV.

Verifica que el "cerebro" (estado/) esté sano y que no haya rutas
absolutas hardcodeadas. Seusa sin argumentos:

    python3 estado/doctor.py

Sale con código 0 si todo está bien, 1 si hay problemas.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (EMPRESAS_SEED_PATH, ESTADO_DIR, HISTORIAL_PATH,  # noqa: E402
                    OUTPUT_DIRS, PROJECT_DIR, RONDAS_PATH, SKILL_SCRIPTS,
                    TAREAS_PATH)
from tracker import CATEGORIES, VACANCY_CATEGORIES, canon_vacancy_key  # noqa: E402

PROBLEMAS = []


def ok(msg):
    print(f"  ✅ {msg}")


def prob(msg):
    PROBLEMAS.append(msg)
    print(f"  ❌ {msg}")


def check_json(path, default):
    if not os.path.exists(path):
        prob(f"falta archivo {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        prob(f"JSON inválido en {path}: {e}")
        return None


def main():
    print(f"doctor — {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")
    print(f"Raíz del proyecto: {PROJECT_DIR}")
    print(f"  (marcador .iducdev-root: {'ok' if os.path.exists(os.path.join(PROJECT_DIR, '.iducdev-root')) else 'FALTA'})\n")

    print("== directorios de output ==")
    for nombre, path in OUTPUT_DIRS.items():
        if path.startswith(PROJECT_DIR) or PROJECT_DIR in path:
            ok(f"{nombre}: {path}")
        else:
            prob(f"{nombre} fuera del proyecto: {path}")
    print()

    print("== cerebro (estado/) ==")
    historial = check_json(HISTORIAL_PATH, None)
    tareas = check_json(TAREAS_PATH, None)
    rondas = check_json(RONDAS_PATH, None)
    for f in (HISTORIAL_PATH, TAREAS_PATH, RONDAS_PATH):
        base = os.path.basename(f)
        if os.path.exists(f):
            ok(f"{base}: presente")
            continue
        prob(f"{base}: falta")
    print()

    print("== integridad del historial ==")
    if historial is not None:
        for cat in CATEGORIES:
            n = len(historial.get(cat, []))
            ok(f"{cat}: {n} items")
        for cat, items in historial.items():
            if cat not in CATEGORIES:
                prob(f"categoría desconocida: {cat}")
                continue
            keys = [i.get("key") for i in items if isinstance(i, dict)]
            dups = len(keys) - len(set(keys))
            # Solo tiene sentido normalizar mayúsculas en claves de texto. Las
            # de `posts_linkedin` son URLs, donde distinguir mayúsculas ES el
            # objetivo: marcarlas como "no normalizadas" era un falso positivo.
            upper = [k for k in keys
                     if k and not str(k).startswith("http") and k.lower() != k]
            if dups:
                prob(f"{cat}: {dups} claves duplicadas")
            if upper:
                prob(f"{cat}: {len(upper)} claves no normalizadas (mayúsculas)")
    print()

    print("== canonización de claves de vacante ==")
    if historial is not None:
        # Una clave de vacante sin pasar por canon_vacancy_key rompe el dedup:
        # la misma vacante puede entrar dos veces si una ronda la escribe como
        # "Empresa::Puesto" y otra como "empresa::puesto". Se comprueba el
        # fichero en seco, sin escribir nada (`tracker normalizar --dry-run`).
        sucias = []
        for cat in VACANCY_CATEGORIES:
            for item in historial.get(cat, []):
                if not isinstance(item, dict):
                    continue
                key = item.get("key", "")
                canon = canon_vacancy_key(key, item)
                if canon and canon != key:
                    sucias.append((cat, key))
        if sucias:
            prob(f"{len(sucias)} clave(s) de vacante sin canonizar; "
                 f"ejecuta: python3 estado/tracker.py normalizar")
            for cat, key in sucias[:3]:
                print(f"         {cat}: {key[:60]}")
        else:
            ok(f"claves de vacante canónicas ({'/'.join(VACANCY_CATEGORIES)})")
    print()

    print("== rutas absolutas hardcodeadas (estado/ y skills) ==")
    pattern = re.compile(r"/home/|iducdev/Escritorio|^~/|/iducdev/")
    revisados = []
    for base in (ESTADO_DIR, os.path.join(PROJECT_DIR, ".opencode", "skills")):
        for root, _dirs, files in os.walk(base):
            if "__pycache__" in root or "tests" in root:
                continue
            revisados.extend(os.path.join(root, f) for f in files
                             if f.endswith(".py") and f != "doctor.py")
    malos = []
    for f in revisados:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                for ln in fh:
                    if pattern.search(ln):
                        malos.append(os.path.relpath(f, PROJECT_DIR))
                        break
        except OSError:
            continue
    if malos:
        prob("rutas absolutas encontradas:")
        for m in sorted(set(malos)):
            print(f"         {m}")
    else:
        ok(f"{len(revisados)} scripts revisados, sin rutas absolutas")
    print()

    print("== scripts de las skills ==")
    for nombre, script in SKILL_SCRIPTS.items():
        if os.path.exists(script):
            ok(f"{nombre}: {script}")
        else:
            prob(f"{nombre}: falta {script}")
    verificador = os.path.join(ESTADO_DIR, "verificar_registro.py")
    (ok if os.path.exists(verificador) else prob)(
        f"verificar_registro: {verificador}" if os.path.exists(verificador)
        else f"verificar_registro: falta {verificador}")
    print()

    print("== semilla de empresas ==")
    if os.path.exists(EMPRESAS_SEED_PATH):
        seed = check_json(EMPRESAS_SEED_PATH, None)
        if seed is not None:
            cands = seed.get("candidates", [])
            sin_dominio = [c for c in cands if not c.get("domain")]
            ok(f"empresas_seed.json: {len(cands)} candidatos")
            if sin_dominio:
                prob(f"{len(sin_dominio)} candidato(s) sin 'domain': sin dominio no "
                     f"hay forma de resolver el tablero (usa 'careers_url')")
    else:
        prob(f"falta {EMPRESAS_SEED_PATH} (verificar_registro.py no tendrá lista)")
    print()

    print("== skills (proyecto) ==")
    skills_dir = os.path.join(PROJECT_DIR, ".opencode", "skills")
    skills = sorted(os.listdir(skills_dir)) if os.path.isdir(skills_dir) else []
    for s in ("asistente-empleo-clientes", "job-search",
              "linkedin-hidden-jobs", "cv-apply", "linkedin-outreach",
              "flutter-employers", "prospectar-clientes"):
        if s in skills:
            ok(s)
        else:
            prob(f"falta skill: {s}")
    print()

    if PROBLEMAS:
        print(f"\n❌ {len(PROBLEMAS)} problema(s) encontrado(s).")
        return 1
    print("\n✅ Asistente en buen estado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())