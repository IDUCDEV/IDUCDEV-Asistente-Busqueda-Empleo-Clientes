#!/usr/bin/env python3
"""empresas_search.py — descubre empresas Flutter sondeando sus tableros de empleo.

Por qué sondea tableros y no portales: los agregadores devuelven 3-25 vacantes
por corrida, mientras que un tablero de empresa (Greenhouse/Ashby/Lever) expone
el listado completo y sin intermediarios. Aquí se prueban empresas concretas y
se extraen solo los roles Flutter/Dart.

Estado persistente:
  estado/empresas_registry.json   empresas conocidas (versionado, sobrevive a reset)
  estado/empresas_cache.json      cache de sondeo (TTL 24 h por defecto)
Salida:
  resultados/empresas-target/{YYYY-MM-DD}-empresas-vacantes.md
  resultados/empresas-target/leads-db.json   (se actualiza status/open_roles)

Uso:
  python3 empresas_search.py                     # 60 empresas, usa cache
  python3 empresas_search.py --limit 20          # solo 20 (rápido)
  python3 empresas_search.py --company nubank    # una empresa concreta
  python3 empresas_search.py --refresh           # ignora la cache
  python3 empresas_search.py --dry-run           # no escribe NADA
  python3 empresas_search.py --stats             # resumen del registro
"""

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
JOB_SEARCH_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "job-search"
)
sys.path.insert(0, JOB_SEARCH_DIR)

# ── Proyecto: ruta resuelta sin hardcodear (config.py + .iducdev-root / env) ──
def _find_project_root():
    env = os.environ.get("IDUCDEV_PROJECT_DIR")
    if env:
        return env
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "estado")) or os.path.exists(os.path.join(d, ".iducdev-root")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


PROJECT_DIR = _find_project_root()
if not PROJECT_DIR:
    sys.exit("No se localizó el proyecto IDUCDEV. Define IDUCDEV_PROJECT_DIR.")
sys.path.insert(0, os.path.join(PROJECT_DIR, "estado"))

from config import (  # noqa: E402
    EMPRESAS_CACHE_PATH, EMPRESAS_CACHE_HORAS, EMPRESAS_FALLOS_MAX,
    EMPRESAS_PAUSA_S, EMPRESAS_REGISTRY_PATH, EMPRESAS_TIMEOUT_S,
    OUTPUT_DIRS,
)
from job_search import has_flutter_dart, normalize_company, normalize_title  # noqa: E402
from tracker import Historial, vacancy_key  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

OUT_DIR = OUTPUT_DIRS["empresas-target"]
LEADS_DB = os.path.join(OUT_DIR, "leads-db.json")
CATEGORY = "vacantes_empresa"

ATS_PROBES = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
}

SUFFIXES = ["", "tech", "techcareers", "digital", "hiring", "careers", "jobs", "labs", "io", "group"]

#Huellas de tablero en la página de carreras de la empresa. Los slugs a ciegas
# fallan casi siempre en LATAM, así que lo fiable es leer la página y deducir
# (proveedor, slug) de lo que la propia empresa enlaza.
ATS_FINGERPRINTS = [
    ("greenhouse", re.compile(
        r"(?:boards|job-boards)\.greenhouse\.io/([a-z0-9\-_]+)"
        r"|greenhouse\.io/embed/job_board\?for=([a-z0-9\-_]+)", re.I)),
    ("ashby", re.compile(
        r"jobs\.ashbyhq\.com/(?:embed\?for=)?([a-z0-9\-_]+)", re.I)),
    ("lever", re.compile(
        r"jobs\.lever\.co/([a-z0-9\-_]+)", re.I)),
    ("workday", re.compile(
        r"([a-z0-9\-]+)\.myworkdayjobs\.com", re.I)),
]

CAREERS_PATHS = ["/careers", "/careers/", "/jobs", "/vacantes", "/empleo", "/trabalhe-conosco"]


def discover_ats(careers_url, timeout=None):
    """Lee la página de carreras y deduce (proveedor, slug).

    Devuelve (ats, slug) o (None, None). Workday se detecta pero no se parsea:
    no expone un JSON público, así que el llamador lo marca para navegador.
    """
    raw = http_get(careers_url, timeout=timeout)
    if raw.startswith("__ERR__") or raw == "__404__":
        return None, None
    for ats, pat in ATS_FINGERPRINTS:
        m = pat.search(raw)
        if m:
            slug = next((g for g in m.groups() if g), None)
            if slug and slug.lower() not in ("embed", "jobs", "en", "es", "index"):
                return ats, slug.lower()
    return None, None


# ── Registro y cache ─────────────────────────────────────────────────

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


def load_registry():
    reg = load_json(EMPRESAS_REGISTRY_PATH, {})
    reg.setdefault("version", 1)
    reg.setdefault("companies", {})
    return reg


def cache_is_fresh(entry, hours=EMPRESAS_CACHE_HORAS):
    if not entry:
        return False
    ts = entry.get("ts")
    if not ts:
        return False
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(ts) < timedelta(hours=hours)
    except (ValueError, TypeError):
        return False


# ── Slugs candidatos ─────────────────────────────────────────────────

def slug_candidates(company):
    """Slugs plausibles para el tablero de una empresa (se prueban en orden)."""
    cands = []

    # 1) Si ya conocemos su página de carreras, el slug suele estar en la URL.
    careers = (company.get("careers_url") or "").lower()
    if careers:
        for m in re.findall(r"(?:greenhouse\.io|ashbyhq\.com|lever\.co)/([a-z0-9\-]+)", careers):
            if m not in cands and m not in ("embed", "jobs", "en", "es"):
                cands.append(m)

    domain = (company.get("domain") or "").lower()
    prefix = domain.split(".")[0].replace("-", "") if domain else ""
    base = re.sub(r"[^a-z0-9]", "", normalize_company(company.get("name", "")))

    for stem in [base, prefix]:
        if not stem:
            continue
        for suf in SUFFIXES:
            s = stem + suf
            if s and s not in cands:
                cands.append(s)
    return cands[:12]


# ── HTTP ─────────────────────────────────────────────────────────────

def http_get(url, timeout=None):
    """Devuelve el cuerpo, o un marcador.

    `__404__` se separa a propósito: un slug inexistente es el caso NORMAL al
    sondear tableros y no debe contar como fallo (ni disparar el cortocircuito).
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/json,text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout or EMPRESAS_TIMEOUT_S) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return "__404__" if e.code == 404 else f"__ERR__:{e.code}"
    except Exception as e:
        return f"__ERR__:{type(e).__name__}"


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# ── Normalizadores por ATS ───────────────────────────────────────────

def norm_greenhouse(data):
    out = []
    for j in (data.get("jobs") or []):
        loc = (j.get("location") or {}).get("name", "") or ""
        out.append({
            "title": (j.get("title") or "").strip(),
            "location": loc,
            "url": j.get("absolute_url", ""),
            "description": strip_html(j.get("content", ""))[:400],
            "published": (j.get("updated_at") or "")[:10],
        })
    return out


def norm_ashby(data):
    out = []
    for j in (data.get("jobs") or []):
        loc = j.get("location") or ""
        if isinstance(loc, dict):
            loc = loc.get("name", "") or ""
        out.append({
            "title": (j.get("title") or "").strip(),
            "location": loc,
            "url": j.get("jobUrl") or j.get("applyUrl") or "",
            "description": (j.get("descriptionPlain") or "")[:400],
            "published": (j.get("publishedAt") or "")[:10],
        })
    return out


def norm_lever(data):
    out = []
    if not isinstance(data, list):
        return out
    for j in data:
        cats = j.get("categories") or {}
        out.append({
            "title": (j.get("text") or "").strip(),
            "location": cats.get("location", "") or "",
            "url": j.get("hostedUrl", ""),
            "description": (j.get("descriptionPlain") or "")[:400],
            "published": str(j.get("createdAt", ""))[:10],
        })
    return out


NORMALIZERS = {"greenhouse": norm_greenhouse, "ashby": norm_ashby, "lever": norm_lever}


# ── Sondeo ───────────────────────────────────────────────────────────

class Prober:
    MAX_INTENTOS = 10  # por empresa: 12 slugs × 3 ATS sería demasiado lento

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.fallos = 0
        self.intentos = 0

    def get(self, url):
        if self.fallos >= EMPRESAS_FALLOS_MAX:
            return None
        raw = http_get(url)
        if raw == "__404__":
            return None  # slug inexistente: normal, no cuenta como fallo
        if raw.startswith("__ERR__"):
            self.fallos += 1
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def probe(self, company):
        """Devuelve (ats, slug, roles) para la primera fuente que responda con vacantes.

        Orden: (1) ats/slug ya conocidos, (2) deducidos de la página de carreras,
        (3) slugs candidatos a ciegas. Los slugs a ciegas casi nunca aciertan en
        LATAM, así que (2) es el paso que realmente rinde.
        """
        # 1) Ya resuelto en el registro.
        if company.get("ats") and company.get("slug") and company["ats"] in ATS_PROBES:
            self.intentos += 1
            data = self.get(ATS_PROBES[company["ats"]].format(slug=company["slug"]))
            if data is not None:
                return company["ats"], company["slug"], NORMALIZERS[company["ats"]](data)

        # 2) Deducir de la página de carreras.
        careers = company.get("careers_url")
        if careers:
            self.intentos += 1
            ats, slug = discover_ats(careers)
            if self.verbose and ats:
                print(f"    · {company['name']} → {ats}/{slug} (deducido de careers_url)")
            if ats == "workday":
                # Sin JSON público: se reporta para que lo mire el navegador.
                return "workday", slug, []
            if ats in ATS_PROBES:
                self.intentos += 1
                data = self.get(ATS_PROBES[ats].format(slug=slug))
                if data is not None:
                    roles = NORMALIZERS[ats](data)
                    if self.verbose:
                        print(f"      ✓ {ats}/{slug}: {len(roles)} roles")
                    return ats, slug, roles
                time.sleep(EMPRESAS_PAUSA_S)

        # 3) Slugs candidatos.
        vacios = None
        for slug in slug_candidates(company):
            for ats, url_tpl in ATS_PROBES.items():
                if self.fallos >= EMPRESAS_FALLOS_MAX or self.intentos >= self.MAX_INTENTOS:
                    # Un tablero que respondió vacío puede ser slug equivocado
                    # (p. ej. greenhouse/nubank existe pero Nubank usa otro):
                    # se reporta, pero nunca como "la empresa no tiene vacantes".
                    return vacios or (None, None, [])
                self.intentos += 1
                url = url_tpl.format(slug=slug)
                if self.verbose:
                    print(f"    · {company['name']} → {ats}/{slug}")
                data = self.get(url)
                if data is None:
                    time.sleep(EMPRESAS_PAUSA_S)
                    continue
                roles = NORMALIZERS[ats](data)
                if not roles:
                    if vacios is None:
                        vacios = (ats, slug, [])
                    time.sleep(EMPRESAS_PAUSA_S)
                    continue
                if self.verbose:
                    print(f"      ✓ {ats}/{slug}: {len(roles)} roles")
                return ats, slug, roles
        return vacios or (None, None, [])


# ── Filtro y scoring ─────────────────────────────────────────────────

MOBILE_RE = re.compile(r"\b(mobile|android|ios|react native|kotlin|swift)\b", re.I)
REMOTE_RE = re.compile(r"remote|remoto|anywhere|home ?office|teletrabajo", re.I)
LATAM_RE = re.compile(
    r"\b(argentina|bolivia|brazil|brasil|chile|colombia|costa ?rica|ecuador|"
    r"guatemala|honduras|m[ée]xico|nicaragua|panam[áa]|paraguay|per[úu]|uruguay|"
    r"venezuela|latam|latin america|am[ée]rica latina)\b", re.I)
SENIORITY_RE = re.compile(
    r"\b(junior|jr\.?|entry|semi[- ]?senior|sr\.?|mid[- ]level|intermediate|senior|staff|lead|principal)\b",
    re.I)
FIT_SENIORITY = ("junior", "jr", "entry", "semi-senior", "mid-level", "intermediate")


def is_latam_friendly(text):
    return bool(LATAM_RE.search(text or ""))


def score_role(role, company):
    """Encaje 0-100. Flutter explícito pesa más que el resto."""
    title = role.get("title", "")
    desc = role.get("description", "")
    blob = f"{title} {desc} {role.get('location','')}"
    s = 0
    if has_flutter_dart(title):
        s += 40
    elif has_flutter_dart(desc):
        s += 15
    if REMOTE_RE.search(blob):
        s += 20
    if is_latam_friendly(blob) or company.get("region") == "latam":
        s += 15
    m = SENIORITY_RE.search(title)
    if m and m.group(1).lower().strip() in FIT_SENIORITY:
        s += 10
    if role.get("published"):
        s += 5
    return min(s, 100)


def select_roles(roles, company):
    """Quedate con los roles relevantes: Flutter/Dart explícito, o móvil para revisar."""
    picked = []
    for r in roles:
        title = r.get("title", "")
        desc = r.get("description", "")
        if has_flutter_dart(title):
            r["review"] = False
        elif MOBILE_RE.search(title) and has_flutter_dart(desc):
            r["review"] = True
        else:
            continue
        r["score"] = score_role(r, company)
        picked.append(r)
    return sorted(picked, key=lambda x: -x["score"])


# ── Informe ──────────────────────────────────────────────────────────

def fmt_report(hits, date_str, time_str, checked, errs):
    lines = [
        f"# Empresas Flutter con vacantes - {date_str}\n",
        f"> 🔎 Sondeo de tableros de empresa · {time_str} UTC · "
        f"{len(hits)} empresas con vacantes Flutter de {checked} sondeadas\n",
        "> 📍 Prioridad: empresas LATAM que contratan LATAM, luego EE.UU. remote-first\n",
    ]
    if not hits:
        lines.append("\n## Sin resultados\n\n> Ninguna empresa con vacante Flutter/Dart.\n")
    for h in hits:
        c = h["company"]
        lines.append(f"## {c['name']} · {len(h['roles'])} vacante(s) · score {h['score']}")
        lines.append(
            f"**Tablero:** {h['ats']}/{h['slug']} | **Región:** {c.get('region','?')} | "
            f"**Tier:** {c.get('tier','?')}"
        )
        if c.get("domain"):
            lines.append(f"**Web:** {c['domain']}\n")
        for r in h["roles"]:
            flag = " ⚠ **verificar:** solo Flutter en la descripción" if r.get("review") else ""
            lines.append(f"### · {r['title']} _(score {r['score']})_")
            lines.append(f"**Ubicación:** {r.get('location') or 'N/A'}")
            if r.get("published"):
                lines.append(f"**⏰** {r['published']}")
            if r.get("url"):
                lines.append(f"**🔗** [{c['name']}]({r['url']})")
            lines.append(flag)
            lines.append("`[Aplicar con cv-apply]`\n")
        lines.append("---\n")
    if errs:
        lines.append("## Notas\n")
        for e in errs[:20]:
            lines.append(f"- ⚠ {e}")
    return "\n".join(lines)


# ── Migración de leads-db.json ───────────────────────────────────────

def migrate_leads_db(registry, dry_run=False):
    """Importa las empresas de resultados/empresas-target/leads-db.json al registro.

    Schema real: {"last_updated": str, "total_runs": int, "companies": [ {...} ]}
    (un dict por fecha también se acepta, por compatibilidad). Cada item trae
    name, website, industry, location, size, funding y tech_stack: de todo eso
    solo sobrevive el nombre, el dominio y una pista de si usan Flutter.
    """
    if not os.path.exists(LEADS_DB):
        return 0
    raw = load_json(LEADS_DB, {})
    if not isinstance(raw, dict):
        return 0

    # Aplanar: cualquier value que sea lista de dicts sirve.
    items = []
    for key, value in raw.items():
        if isinstance(value, list):
            items.extend(v for v in value if isinstance(v, dict))

    added = 0
    today = datetime.now(timezone.utc).date().isoformat()
    for it in items:
        name = (it.get("nombre") or it.get("empresa") or it.get("name") or "").strip()
        if not name:
            continue
        key = normalize_company(name)
        if not key or key in registry["companies"]:
            continue
        domain = it.get("dominio") or it.get("domain") or it.get("website") or ""
        if domain.startswith("http"):
            domain = re.sub(r"^https?://(www\.)?", "", domain).split("/")[0]
        stack = " ".join(str(t) for t in (it.get("tech_stack") or []))
        usa_flutter = "flutter" in stack.lower() or "dart" in stack.lower()
        loc = it.get("location") or it.get("ubicacion") or ""
        region = "us" if re.search(r"united states|estados unidos|\busa\b|\bcanada\b",
                                   loc, re.I) else "latam"
        registry["companies"][key] = {
            "key": key,
            "name": name,
            "domain": domain,
            "region": region,
            # tech_stack con Flutter/Dart prueba que la empresa usa el stack:
            # vale la pena sondearla antes que una empresa genérica.
            "tier": 1 if usa_flutter else 3,
            "status": "nuevo",
            "added": today,
            "last_checked": None,
            "open_roles": 0,
            "source": "migracion leads-db",
            "careers_url": it.get("careers_url") or it.get("url") or "",
            "industry": it.get("industry") or "",
            "usa_flutter": usa_flutter,
        }
        added += 1
    return added


# ── Main ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=60, help="Máximo de empresas a sondear")
    ap.add_argument("--company", help="Sondea solo una empresa (nombre o clave)")
    ap.add_argument("--refresh", action="store_true", help="Ignora la cache")
    ap.add_argument("--dry-run", action="store_true", help="No escribe NADA (ni registro, ni cache, ni .md)")
    ap.add_argument("--stats", action="store_true", help="Resumen del registro y sale")
    ap.add_argument("--verbose", action="store_true", help="Muestra cada sondeo")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    date_str, time_str = now.strftime("%Y-%m-%d"), now.strftime("%H:%M")

    registry = load_registry()
    companies = registry["companies"]

    if args.stats:
        counts = {}
        for c in companies.values():
            counts[c.get("status", "nuevo")] = counts.get(c.get("status", "nuevo"), 0) + 1
        regions = {}
        for c in companies.values():
            regions[c.get("region", "?")] = regions.get(c.get("region", "?"), 0) + 1
        print(f"Empresas en registro: {len(companies)}")
        print("Por estado:", counts)
        print("Por región:", regions)
        print("---STATS---")
        print(f"empresas: {len(companies)}")
        for k, v in sorted(counts.items()):
            print(f"{k}: {v}")
        return

    # Seed/migración: idempotente, corre siempre. Importa de leads-db.json las
    # empresas que aún no estén en el registro (saltando las ya presentes).
    added = migrate_leads_db(registry, dry_run=args.dry_run)
    if added and not args.dry_run:
        registry["updated"] = date_str
        save_json(EMPRESAS_REGISTRY_PATH, registry)
        print(f"[seed] {added} empresas migradas de leads-db.json")
    elif added:
        print(f"[seed:dry-run] {added} empresas a migrar de leads-db.json")
    companies = registry["companies"]
    if args.company:
        key = normalize_company(args.company)
        cands = [c for c in companies.values()
                 if c["key"] == key or args.company.lower() in c["name"].lower()]
        if not cands:
            print(f"Empresa '{args.company}' no está en el registro.")
            print("---ERRORS---")
            print(f"no encontrada: {args.company}")
            return
        targets = cands
    else:
        # Prioridad: sin sondear > con vacante > todo lo demás; y Tier 1 LATAM primero.
        targets = sorted(
            companies.values(),
            key=lambda c: (
                0 if c.get("status") == "nuevo" else 1,
                c.get("tier", 9) if isinstance(c.get("tier"), int) else 9,
                0 if c.get("region") == "latam" else 1,
            ),
        )[: args.limit]

    cache = load_json(EMPRESAS_CACHE_PATH, {})
    prober = Prober(verbose=args.verbose)
    hits, errs, checked, skipped = [], [], 0, 0

    hist = Historial() if not args.dry_run else None

    for c in targets:
        key = c["key"]
        ckey = cache.get(key)
        if not args.refresh and cache_is_fresh(ckey):
            ats, slug, roles = ckey["ats"], ckey["slug"], ckey["roles"]
        else:
            checked += 1
            ats, slug, roles = prober.probe(c)
            if ats and not args.dry_run:
                cache[key] = {"ts": now.isoformat(timespec="seconds"), "ats": ats,
                              "slug": slug, "roles": roles}
            time.sleep(EMPRESAS_PAUSA_S)

        if not ats:
            errs.append(f"{c['name']}: sin tablero localizado")
            if not args.dry_run:
                c["status"] = c.get("status") or "sin_tablero"
            continue
        if ats == "workday":
            errs.append(f"{c['name']}: tablero Workday (sin API pública) → revisar en navegador")
            if not args.dry_run:
                c["ats"], c["slug"] = ats, slug
                c["last_checked"] = now.isoformat(timespec="seconds")
                c["status"] = "revisar_navegador"
            continue

        selected = select_roles(roles, c)
        if not args.dry_run:
            c["ats"], c["slug"] = ats, slug
            c["last_checked"] = now.isoformat(timespec="seconds")
            c["open_roles"] = len(selected)
            if selected:
                c["status"] = "con_vacante"
            elif roles:
                # El tablero tiene vacantes pero ninguna de Flutter.
                c["status"] = "sin_vacante_flutter"
            else:
                c["status"] = "tablero_vacio"
        if not selected:
            continue

        best = max(r["score"] for r in selected)
        hits.append({"company": c, "ats": ats, "slug": slug, "roles": selected, "score": best})

        # Dedup central: no re-listar vacantes ya vistas en días anteriores.
        for r in selected:
            if not hist:
                continue
            vkey = vacancy_key(c["name"], r["title"])
            prev = hist.get(CATEGORY, vkey)
            if not prev or (prev.get("fecha_visto") or "").startswith(date_str):
                hist.add(CATEGORY, vkey, meta={
                    "empresa": c["name"],
                    "titulo": r["title"],
                    "url": r.get("url", ""),
                    "tablero": f"{ats}/{slug}",
                    "score": r["score"],
                })
            else:
                skipped += 1

    if not args.dry_run:
        registry["updated"] = date_str
        save_json(EMPRESAS_REGISTRY_PATH, registry)
        save_json(EMPRESAS_CACHE_PATH, cache)
        if hist:
            hist.save()
        os.makedirs(OUT_DIR, exist_ok=True)
        out_path = os.path.join(OUT_DIR, f"{date_str}-empresas-vacantes.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(fmt_report(hits, date_str, time_str, checked, errs))
        print(out_path)
    else:
        print("[dry-run] no se escribió registro, cache, historial ni informe")
        print(fmt_report(hits, date_str, time_str, checked, errs))

    print("---JOBCOUNT---")
    print(sum(len(h["roles"]) for h in hits))
    print("---SKIPPED---")
    print(skipped)
    print("---SOURCES---")
    for h in hits:
        print(f"{h['company']['name']} ({h['ats']}): {len(h['roles'])}")
    print("---ERRORS---")
    for e in errs[:20]:
        print(e)


if __name__ == "__main__":
    main()
