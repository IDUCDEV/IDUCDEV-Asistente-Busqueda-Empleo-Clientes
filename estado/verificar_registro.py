#!/usr/bin/env python3
"""verificar_registro.py — Da de alta empresas al registro SOLO si su tablero ATS responde.

Por qué existe: el registro crece con empresas, pero un slug adivinado a ciegas
casi nunca acierta en LATAM, así que "añadir 100 empresas hoping" solo produce
ruido y peticiones infinitas. Este script invierte el problema:

    semilla (empresas_seed.json) → probar tabl��ros → registrar lo que funciona

Es decir, la verificación es EMPÍRICA, no declarativa: una empresa entra al
registro cuando su endpoint público devuelve ≥1 vacante real, y se guardan `ats`
+ `slug` para que las próximas rondas vayan por el camino corto (path 1 del
`Prober`). Con eso "verified on entry" es una garantía, no una intención.

Uso:
    python3 estado/verificar_registro.py --stats        # estado del registro y la semilla
    python3 estado/verificar_registro.py --dry-run      # prueba, no escribe NADA
    python3 estado/verificar_registro.py --limit 40     # prueba N candidatos
    python3 estado/verificar_registro.py                # prueba la semilla entera y registra

Notas:
  · No requiere navegador ni APIs de pago: los cuatro tableros (Greenhouse,
    Ashby, Lever, Workday) exponen JSON público.
  · Es idempotente: una empresa ya en el registro solo se refresca (ats/slug/
    open_roles), nunca se duplica.
  · No toca empresas ya registradas salvo que su tablero haya pasado a responder.
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (  # noqa: E402
    EMPRESAS_REGISTRY_PATH, EMPRESAS_SEED_PATH, EMPRESAS_TIMEOUT_S,
    EMPRESAS_WORKERS, PROJECT_DIR,
)
from tracker import normalize_company  # noqa: E402

SKILLS_DIR = os.path.join(PROJECT_DIR, ".opencode", "skills")
EMP_DIR = os.path.join(SKILLS_DIR, "flutter-employers")
sys.path.insert(0, EMP_DIR)

import empresas_search as es  # noqa: E402

SEED_PATH = EMPRESAS_SEED_PATH


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fmt_stats(registry, seed):
    cs = registry.get("companies", {})
    cands = seed.get("candidates", [])
    print(f"== registro ==\n  empresas: {len(cs)}")
    by_region = {}
    for c in cs.values():
        by_region[c.get("region", "?")] = by_region.get(c.get("region", "?"), 0) + 1
    print("  por región: " + ", ".join(f"{k}={v}" for k, v in sorted(by_region.items())))
    with_ats = sum(1 for c in cs.values() if c.get("ats") and c.get("slug"))
    with_careers = sum(1 for c in cs.values() if c.get("careers_url"))
    with_vac = sum(1 for c in cs.values() if c.get("open_roles"))
    print(f"  con ats+slug: {with_ats} | con careers_url: {with_careers} "
          f"| con vacantes: {with_vac}")
    keys = set(cs)
    pend = [c for c in cands if normalize_company(c.get("name", "")) not in keys]
    print(f"\n== semilla ==\n  candidatos: {len(cands)} | ya en registro: "
          f"{len(cands) - len(pend)} | pendientes: {len(pend)}")
    if pend:
        print("  primeros pendientes: " +
              ", ".join(c["name"] for c in pend[:12]))


def main():
    ap = argparse.ArgumentParser(description="Verifica tableros y da de alta empresas")
    ap.add_argument("--dry-run", action="store_true",
                    help="Prueba la semilla y muestra qué entraría, sin escribir")
    ap.add_argument("--limit", type=int, default=0,
                    help="Máximo de candidatos a probar (0 = todos)")
    ap.add_argument("--stats", action="store_true", help="Resumen y sale")
    ap.add_argument("--verbose", action="store_true", help="Muestra cada sondeo")
    ap.add_argument("--slugs-ciegos", action="store_true", dest="slugs_ciegos",
                    help="Prueba slugs adivinados si falla la página de carreras")
    args = ap.parse_args()

    registry = load_json(EMPRESAS_REGISTRY_PATH, {"version": 1, "companies": {}})
    registry.setdefault("version", 1)
    registry.setdefault("companies", {})
    seed = load_json(SEED_PATH, {"candidates": []})

    if args.stats:
        fmt_stats(registry, seed)
        return 0

    candidates = seed.get("candidates", [])

    # Además de la semilla, se re-sondean las empresas YA registradas cuyo
    # tablero no está resuelto. Sirve para dos cosas: arreglar placeholders viejos
    # (había entradas con ats="workday" y slug="wd12", de cuando Workday no
    # tenía API) y resolver las que solo tienen un dominio pero nunca se
    # sondearon. Van al final: la semilla es lo prioritario.
    def ats_utilizable(entry):
        ats, slug = entry.get("ats") or "", entry.get("slug") or ""
        if not slug:
            return False
        return ats in es.ATS_PROBES or ats.startswith("workday:")

    ya_resueltas = {k for k, e in registry["companies"].items()
                    if ats_utilizable(e)}
    for key, entry in registry["companies"].items():
        if key in ya_resueltas or not entry.get("domain"):
            continue
        candidates.append({"name": entry["name"], "domain": entry["domain"],
                           "region": entry.get("region", "global"),
                           "tier": entry.get("tier", 3)})

    if args.limit:
        candidates = candidates[:args.limit]
    if not candidates:
        print("No hay candidatos en empresas_seed.json.")
        return 1

    now = datetime.now(timezone.utc)
    today = now.date().isoformat()

    def sondear(cand):
        """Prueba el tablero de UN candidato. Cada hilo lleva su propio Prober:
        los contadores (`_usados` sobre todo) son por empresa y compartirlos
        entre hilos los corrompería."""
        key = normalize_company(cand.get("name", ""))
        if not key:
            return None
        company = {
            "key": key,
            "name": cand["name"],
            "domain": cand.get("domain", ""),
            "region": cand.get("region", "global"),
            "tier": cand.get("tier", 3),
        }
        prober = es.Prober(verbose=args.verbose, slug_ciegos=args.slugs_ciegos)
        ats, slug, roles = prober.probe(company)
        time.sleep(es.EMPRESAS_PAUSA_S)
        return {"company": company, "ats": ats, "slug": slug, "roles": roles,
                "fallos": prober.fallos, "intentos": prober.intentos,
                "resolution": prober.resolution,
                "careers_url": prober.last_careers_url or ""}

    print(f"Probando {len(candidates)} candidatos con {EMPRESAS_WORKERS} hilos…",
          flush=True)
    resultados = []
    with ThreadPoolExecutor(max_workers=EMPRESAS_WORKERS) as pool:
        # Progreso en vivo: sin esto una corrida de 15-50 min parece colgada y no
        # hay forma de saber si va bien. Los resultados llegan en orden de la
        # semilla, así que se imprime cada uno (acierto o no) con el avance.
        for i, res in enumerate(pool.map(sondear, candidates), 1):
            if res is not None:
                resultados.append(res)
            if res is None:
                continue
            nombre = res["company"]["name"]
            if res["ats"]:
                print(f"  [{i}/{len(candidates)}] ✓ {nombre} → "
                      f"{res['ats']}/{res['slug']} ({len(res['roles'])} roles)",
                      flush=True)
            elif args.verbose:
                print(f"  [{i}/{len(candidates)}] · {nombre} → sin tablero",
                      flush=True)

    nuevos, refrescados, sin_tablero = [], [], []
    for res in resultados:
        if res is None:
            continue
        company = res["company"]
        ats, slug, roles = res["ats"], res["slug"], res["roles"]
        if not ats:
            sin_tablero.append(company["name"])
            continue
        # Solo se registra lo que tiene vacantes reales. Pero hay un matiz: un
        # tablero vacío puede significar dos cosas según de dónde salió el slug.
        #   · "careers"  → lo dedujo la página de la propia empresa: el slug es
        #     fiable, así que 0 vacantes ES "no hay vacantes" y el tablero se
        #     guarda igual (da de altas y, sobre todo, arregla placeholders viejos).
        #   · "ciego"    → el slug se adivinó: vacío casi siempre es slug
        #     equivocado, así que no se registra nada.
        if not roles and res["resolution"] != "careers":
            sin_tablero.append(f"{company['name']}(tablero vacío, slug adivinado)")
            continue

        selected = es.select_roles(roles, company)
        entry = registry["companies"].get(company["key"])
        status = "con_vacante" if selected else "sin_vacante_flutter"
        if entry:
            reparado = (entry.get("ats"), entry.get("slug")) != (ats, slug)
            refrescados.append(company["name"] + (" (reparado)" if reparado else ""))
            if not args.dry_run:
                entry.update({"ats": ats, "slug": slug, "region": company["region"],
                              "tier": company["tier"], "domain": company["domain"],
                              "last_checked": now.isoformat(timespec="seconds"),
                              "open_roles": len(selected), "status": status})
                # La página que reveló el tablero vale más que una adivinada:
                # se guarda para las próximas rondas.
                if res["careers_url"]:
                    entry["careers_url"] = res["careers_url"]
        else:
            nuevos.append((company["name"], ats, slug, len(selected)))
            if not args.dry_run:
                registry["companies"][company["key"]] = {
                    "key": company["key"], "name": company["name"],
                    "domain": company["domain"], "region": company["region"],
                    "tier": company["tier"], "status": status,
                    "added": today, "last_checked": now.isoformat(timespec="seconds"),
                    "open_roles": len(selected), "ats": ats, "slug": slug,
                    "careers_url": res["careers_url"],
                    "source": "verificar_registro (tablero verificado)",
                }

    if not args.dry_run:
        registry["updated"] = today
        registry["version"] = max(registry.get("version", 1), 2)
        save_json(EMPRESAS_REGISTRY_PATH, registry)
    else:
        print("[dry-run] no se escribió el registro")

    print("---RESUMEN---")
    print(f"  candidatos probados: {len(candidates)}")
    print(f"  nuevas empresas registradas: {len(nuevos)}")
    for name, ats, slug, n in sorted(nuevos, key=lambda x: -x[3]):
        print(f"    + {name:26} → {ats}/{slug} ({n} Flutter)")
    print(f"  ya existentes refrescadas: {len(refrescados)}")
    print(f"  sin tablero (no registradas): {len(sin_tablero)}")
    print(f"  total en registro: {len(registry['companies'])}")
    print("---FAULTS---")
    print(f"  {sum(r['fallos'] for r in resultados if r)} fallo(s) HTTP; "
          f"{sum(r['intentos'] for r in resultados if r)} intento(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())