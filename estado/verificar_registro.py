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
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (  # noqa: E402
    EMPRESAS_REGISTRY_PATH, EMPRESAS_SEED_PATH, EMPRESAS_TIMEOUT_S,
    EMPRESAS_WORKERS, PROJECT_DIR,
)
from tracker import canon_domain, canon_name, names_similar, normalize_company  # noqa: E402

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


STATUS_RANK = {
    "con_vacante": 5, "sin_vacante_flutter": 4, "tablero_vacio": 3,
    "sin_tablero": 2, "sin_dominio": 1, "nuevo": 0,
}


def _board_plausible(entry):
    """¿El slug del tablero se parece al nombre/dominio de la empresa?

    Detecta boards heredados de un slug adivinado (p. ej. "Remote" apuntando a
    greenhouse/attotude, que es otra empresa). Sin esto, al fusionar duplicados
    se conservaba un tablero que no era de la empresa.
    """
    slug_raw = entry.get("slug") or ""
    if (entry.get("ats") or "").startswith("teamtailor"):
        # "jobs.storytel.com" o "acme.teamtailor.com" → "storytel"/"acme".
        parts = [p for p in slug_raw.split(".")
                 if p not in ("www", "jobs", "careers", "teamtailor", "com")]
        slug_raw = parts[0] if parts else ""
    else:
        slug_raw = slug_raw.split(".")[0]
    slug = canon_name(slug_raw)
    name = canon_name(entry.get("name"))
    dom = canon_name(canon_domain(entry.get("domain")).split(".")[0])
    if not slug:
        return False
    return bool((name and (slug in name or name in slug))
                or (dom and (slug in dom or dom in slug)))


def _merge_into(dst, src):
    """Completa dst con lo que falte en src, sin pisar lo verificado."""
    reset = False
    d_ats, d_slug = dst.get("ats"), dst.get("slug")
    s_ats, s_slug = src.get("ats"), src.get("slug")
    if d_ats and d_slug and s_ats and s_slug and (d_ats, d_slug) != (s_ats, s_slug):
        dp, sp = _board_plausible(dst), _board_plausible(src)
        if sp and not dp:
            dst["ats"], dst["slug"] = s_ats, s_slug
            dst["careers_url"] = src.get("careers_url") or dst.get("careers_url")
        elif not dp and not sp:
            # Dos tableros distintos y ninguno encaja: no hay forma de saber
            # cuál es el bueno, así que se deja sin resolver para re-sondearlo.
            dst.pop("ats", None)
            dst.pop("slug", None)
            reset = True

    for k, v in src.items():
        if k in ("key", "name", "added", "aliases"):
            continue
        if not dst.get(k) and v:
            dst[k] = v
    dst["open_roles"] = max(dst.get("open_roles") or 0, src.get("open_roles") or 0)
    if reset:
        dst["status"] = "nuevo"
        dst["last_checked"] = None
    elif STATUS_RANK.get(src.get("status"), -1) > STATUS_RANK.get(dst.get("status"), -1):
        dst["status"] = src.get("status")
    aliases = set(dst.get("aliases") or [])
    aliases.add(src.get("key") or "")
    aliases.update(src.get("aliases") or [])
    aliases.discard(dst.get("key"))
    if aliases:
        dst["aliases"] = sorted(a for a in aliases if a)


def podar_registro(registry, dry_run=False):
    """Limpia el registro: marca las entradas sin dominio y fusiona duplicados.

    No borra información: los duplicados se fusionan en una entrada canónica
    (conservando los alias) y las entradas sin dominio pasan a `sin_dominio`,
    que el sondeo ignora. Así dejan de consumir ronda y de ensuciar el informe.
    """
    cs = registry.get("companies", {})
    acciones = []

    for key, c in list(cs.items()):
        if (not c.get("domain") and not c.get("ats")
                and c.get("status") not in ("con_vacante", "sin_vacante_flutter")):
            if c.get("status") != "sin_dominio":
                acciones.append(f"sin dominio → {key}")
                if not dry_run:
                    c["status"] = "sin_dominio"

    # Union-find por nombre canónico, dominio y prefijo de nombre.
    parent = {k: k for k in cs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    keys = list(cs)
    for i, a in enumerate(keys):
        ca, na, da = cs[a], canon_name(cs[a].get("name")), canon_domain(cs[a].get("domain"))
        for b in keys[i + 1:]:
            cb, nb, db = cs[b], canon_name(cs[b].get("name")), canon_domain(cs[b].get("domain"))
            same = (na and na == nb) or (da and da == db)
            if not same and na and nb and ca.get("region") == cb.get("region"):
                # "Propi" / "Propi Latam", "Serasa" / "Serasa Experian" y las
                # variantes de acentuación ("Su Musica" / "Sua Música").
                same = names_similar(na, nb)
            if same:
                union(a, b)

    grupos = {}
    for k in keys:
        grupos.setdefault(find(k), []).append(k)

    for raiz, miembros in grupos.items():
        if len(miembros) < 2:
            continue
        # Sobrevive la entrada con tablero verificado; si no, la más antigua.
        def prioridad(k):
            c = cs[k]
            return (0 if (c.get("ats") and c.get("slug")) else 1,
                    c.get("added") or "9999-12-31", len(k))
        survivor = sorted(miembros, key=prioridad)[0]
        for k in miembros:
            if k == survivor:
                continue
            acciones.append(f"duplicado: {k} → {survivor}")
            if not dry_run:
                _merge_into(cs[survivor], cs[k])
                cs.pop(k, None)

    return acciones


def fmt_stats(registry, seed):
    cs = registry.get("companies", {})
    cands = seed.get("candidates", [])
    print(f"== registro ==\n  empresas: {len(cs)}")
    by_status = {}
    for c in cs.values():
        st = c.get("status", "nuevo")
        by_status[st] = by_status.get(st, 0) + 1
    print("  por estado: " + ", ".join(f"{k}={v}" for k, v in sorted(by_status.items())))
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
    ap.add_argument("--podar", action="store_true",
                    help="Marca sin_dominio y fusiona empresas duplicadas")
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

    if args.podar:
        acciones = podar_registro(registry, dry_run=args.dry_run)
        for a in acciones:
            print(f"  · {a}")
        if not acciones:
            print("Registro ya limpio: nada que podar.")
        elif args.dry_run:
            print(f"[dry-run] {len(acciones)} acción(es) no aplicadas")
        else:
            registry["updated"] = datetime.now(timezone.utc).date().isoformat()
            save_json(EMPRESAS_REGISTRY_PATH, registry)
            print(f"{len(acciones)} acción(es) aplicadas; "
                  f"empresas ahora: {len(registry['companies'])}")
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

    nuevos, refrescados, sin_tablero = [], [], []

    def aplicar(res):
        """Clasifica un sondeo y actualiza el registro (no escribe a disco)."""
        company = res["company"]
        ats, slug, roles = res["ats"], res["slug"], res["roles"]
        if not ats:
            sin_tablero.append(company["name"])
            return
        # Solo se registra lo que tiene vacantes reales. Pero hay un matiz: un
        # tablero vacío puede significar dos cosas según de dónde salió el slug.
        #   · "careers"  → lo dedujo la página de la propia empresa: el slug es
        #     fiable, así que 0 vacantes ES "no hay vacantes" y el tablero se
        #     guarda igual (da de altas y, sobre todo, arregla placeholders viejos).
        #   · "ciego"    → el slug se adivinó: vacío casi siempre es slug
        #     equivocado, así que no se registra nada.
        if not roles and res["resolution"] != "careers":
            sin_tablero.append(f"{company['name']}(tablero vacío, slug adivinado)")
            return

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

    def guardar():
        if args.dry_run:
            return
        registry["updated"] = today
        registry["version"] = max(registry.get("version", 1), 2)
        save_json(EMPRESAS_REGISTRY_PATH, registry)

    print(f"Probando {len(candidates)} candidatos con {EMPRESAS_WORKERS} hilos…",
          flush=True)
    resultados = []
    with ThreadPoolExecutor(max_workers=EMPRESAS_WORKERS) as pool:
        # Progreso en vivo: sin esto una corrida de 15-50 min parece colgada y no
        # hay forma de saber si va bien. Los resultados llegan en orden de la
        # semilla, así que se imprime cada uno (acierto o no) con el avance.
        # Cada resultado se aplica en cuanto llega y se guarda cada 15: antes TODO
        # se escribía al final, así que una interrupción (timeout, Ctrl-C,
        # reinicio) tiraba la corrida completa.
        for i, res in enumerate(pool.map(sondear, candidates), 1):
            if res is None:
                continue
            resultados.append(res)
            aplicar(res)
            if i % 15 == 0:
                guardar()
            nombre = res["company"]["name"]
            if res["ats"]:
                print(f"  [{i}/{len(candidates)}] ✓ {nombre} → "
                      f"{res['ats']}/{res['slug']} ({len(res['roles'])} roles)",
                      flush=True)
            elif args.verbose:
                print(f"  [{i}/{len(candidates)}] · {nombre} → sin tablero",
                      flush=True)

    guardar()
    if args.dry_run:
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