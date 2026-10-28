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
  python3 empresas_search.py --nuevas            # solo lo no visto (delta)
  python3 empresas_search.py --no-encolar        # no tocar la cola
  python3 empresas_search.py --dry-run           # no escribe NADA
  python3 empresas_search.py --stats             # resumen del registro
  python3 empresas_search.py --min-score 45      # solo roles con buen encaje

Tableros soportados: Greenhouse, Ashby, Lever, Workable, Recruitee, Teamtailor,
SmartRecruiters, BambooHR y Personio (JSON/XML GET público), más Workday (CXS,
JSON POST público). Todos exponen la vacante sin credenciales; lo que NO se
automatiza es el ENVÍO de la postulación (reCAPTCHA invisible + formulario
renderizado por JS): eso lo hace el usuario en su navegador.
"""

import argparse
import copy
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    EMPRESAS_CACHE_PATH, EMPRESAS_CACHE_HORAS, EMPRESAS_CAREERS_TIMEOUT_S,
    EMPRESAS_FALLOS_MAX, EMPRESAS_PAUSA_S, EMPRESAS_REGISTRY_PATH,
    EMPRESAS_TIMEOUT_S, EMPRESAS_WORKERS, OUTPUT_DIRS,
)
from job_search import has_flutter_dart, normalize_company, normalize_title  # noqa: E402
from tracker import (  # noqa: E402
    Historial, canon_domain, canon_name, names_similar, vacancy_key,
)

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
    # Los seis siguientes cubren el hueco real de LATAM/EU: sus tableros viven
    # en un subdominio de la propia empresa y por eso no aparecían al buscar
    # enlaces de Greenhouse/Ashby/Lever en /careers.
    "workable": "https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true",
    "recruitee": "https://{slug}.recruitee.com/api/offers/",
    # Teamtailor se codifica como host completo (sirve tanto jobs.empresa.com
    # como empresa.teamtailor.com) y su feed público es /jobs.json.
    "teamtailor": "https://{slug}/jobs.json",
    "smartrecruiters": "https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100",
    "bamboohr": "https://{slug}.bamboohr.com/careers/list",
    "personio": "https://{slug}.jobs.personio.de/xml?language=en",
}

# Variantes de URL para un mismo proveedor (Personio usa .de y .com según país).
ATS_URL_ALTS = {
    "personio": ["https://{slug}.jobs.personio.com/xml?language=en"],
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
    # Workday: 3 grupos (host, locale, site). El host trae el subdominio del
    # tenant ("rappi.wd12.myworkdayjobs.com") y el site va tras el locale.
    ("workday", re.compile(
        r"(?:https?://)?([a-z0-9][a-z0-9\-]*\.[a-z0-9\-]+\.myworkdayjobs\.com)/"
        r"([a-z]{2}(?:-[A-Za-z]{2,4})?/)?([A-Za-z0-9_\-]+)",
        re.I)),
    # Los tableros "de subdominio" se detectan igual de fácil que los tres
    # grandes; antes se ignoraban y la empresa acababa como "sin tablero".
    ("workable", re.compile(
        r"apply\.workable\.com/([a-z0-9\-_]+)"
        r"|([a-z0-9\-_]+)\.workable\.com", re.I)),
    ("recruitee", re.compile(r"([a-z0-9\-_]+)\.recruitee\.com", re.I)),
    # Teamtailor no siempre usa subdominio propio: el career site puede vivir
    # en jobs.empresa.com. La huella `teamtailor-cdn.com` está también ahí, así
    # que el slug se resuelve al host de la página (ver discover_ats).
    ("teamtailor", re.compile(
        r"([a-z0-9\-_]+)\.teamtailor\.com|teamtailor-cdn\.com", re.I)),
    ("smartrecruiters", re.compile(
        r"(?:careers|jobs)\.smartrecruiters\.com/([a-z0-9\-_]+)", re.I)),
    ("bamboohr", re.compile(r"([a-z0-9\-_]+)\.bamboohr\.com", re.I)),
    ("personio", re.compile(
        r"([a-z0-9\-_]+)\.jobs\.personio\.(?:com|de)", re.I)),
]

# Rutas de página de carreras que se prueban, en orden de probabilidad.
# Sin duplicados con barra final: la mayoría de servidores redirige "/careers/"
# a "/careers" y probarlo dos veces solo cuesta un timeout.
CAREERS_PATHS = ["/careers", "/jobs", "/vacantes", "/empleo", "/trabalhe-conosco"]


def discover_ats(careers_url, timeout=None, raw=None):
    """Deduce (proveedor, slug) del HTML de una página de carreras.

    Devuelve (ats, slug) o (None, None). Si se pasa `raw`, no descarga nada: usa
    ese cuerpo ya descargado (así `resolve_board` puede distinguir "el dominio no
    resuelve" de "esta ruta no existe" sin gastar una petición extra).

    Workday sí tiene endpoint JSON público (CXS), pero su URL se arma con tres
    piezas (host, locale, site) que no encajan en el par (ats, slug) de los
    otros tres proveedores. Se codifica así: `ats` = "workday:<host>" y `slug` =
    "<locale>/<site>" (el path de navegación, que es lo que se ve en la web).
    """
    if raw is None:
        raw = http_get(careers_url, timeout=timeout)
    if raw.startswith("__ERR__") or raw.startswith("__NET__") or raw == "__404__":
        return None, None
    for ats, pat in ATS_FINGERPRINTS:
        m = pat.search(raw)
        if not m:
            continue
        if ats == "workday":
            host, locale, site = m.group(1), m.group(2) or "", m.group(3)
            if not (host and site) or site.lower() in ("index", "jobs", "embed"):
                continue
            return f"workday:{host.lower()}", f"{locale}{site}"
        if ats == "teamtailor":
            # Con subdominio propio el slug es el host; en un dominio custom
            # (jobs.empresa.com) el feed vive en el mismo host que la página.
            sub = m.group(1)
            host = (f"{sub.lower()}.teamtailor.com" if sub
                    else urllib.parse.urlparse(careers_url).netloc.lower())
            if host:
                return "teamtailor", host
            continue
        slug = next((g for g in m.groups() if g), None)
        if slug and slug.lower() not in ("embed", "jobs", "en", "es", "index"):
            return ats, slug.lower()
    return None, None


def careers_url_candidates(company):
    """URLs de carrera plausibles a partir del dominio, en orden de probabilidad."""
    domain = (company.get("domain") or "").strip()
    if not domain:
        return []
    domain = re.sub(r"^https?://", "", domain).split("/")[0]
    base = f"https://{domain}"
    urls = [company["careers_url"]] if company.get("careers_url") else []
    for path in CAREERS_PATHS:
        u = base + path
        if u not in urls:
            urls.append(u)
    return urls


def resolve_board(company, timeout=None):
    """Deduce (ats, slug) leyendo las páginas de carrera de la empresa.

    Es el paso que de verdad acierta: leer /careers y deducir de lo que la propia
    empresa enlaza, en vez de adivinar slugs.

    Dos decisiones de rendimiento, ambas medidas:
      · timeout corto (EMPRESAS_CAREERS_TIMEOUT_S): se prueban varias rutas y los
        dominios muertos son la norma (nunez.com.ar tardaba 79 s en 6 URLs);
      · **corta en el primer `__NET__`**: si el dominio no resuelve, las otras
        rutas del mismo dominio tampoco van a resolver, así que no se prueban.
        Es lo que separa una ronda de 50 minutos de una de 15.

    Devuelve (ats, slug, careers_url) o (None, None, None).
    """
    if timeout is None:
        timeout = EMPRESAS_CAREERS_TIMEOUT_S
    for url in careers_url_candidates(company):
        raw = http_get(url, timeout=timeout)
        ats, slug = discover_ats(url, raw=raw)
        if ats:
            return ats, slug, url
        if raw == "__NET__":
            break  # dominio muerto: no hay nada que probar en las demás rutas
    return None, None, None


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

    Los marcadores están separados a propósito porque significan cosas distintas:
      - `__404__`  slug inexistente: el caso NORMAL al sondear tableros.
      - `__NET__`  el host no resuelve o no conecta (DNS muerto, subdominio
        retirado). No es "el sitio nos bloquea", así que NO debe contar como
        fallo ni disparar el cortocircuito: lo correcto es probar el siguiente
        candidato (típico en Workday, donde el tenant cambia de subdominio).
      - `__ERR__:` cualquier otro error (403, 429, 5xx): sí cuenta como fallo.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/json,text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout or EMPRESAS_TIMEOUT_S) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return "__404__" if e.code == 404 else f"__ERR__:{e.code}"
    except urllib.error.URLError:
        return "__NET__"
    except Exception as e:
        return f"__ERR__:{type(e).__name__}"


def http_post_json(url, payload, timeout=None):
    """POST JSON → texto del cuerpo, o el mismo juego de marcadores que http_get.

    Es lo que necesita el endpoint CXS de Workday, que es POST puro (su GET
    devuelve 405). Es un endpoint **público** de solo lectura: la misma
    EmploymentSite pública que el navegador consulta, sin credenciales.
    """
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout or EMPRESAS_TIMEOUT_S) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return "__404__" if e.code == 404 else f"__ERR__:{e.code}"
    except urllib.error.URLError:
        return "__NET__"
    except Exception as e:
        return f"__ERR__:{type(e).__name__}"


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# ── Workday (endpoint público CXS) ────────────────────────────────────
# La premisa de que "Workday no expone JSON público" era falsa: el EmploymentSite
# sirve la búsqueda con
#   POST https://<host>/wday/cxs/<tenant>/<site>/jobs
#   {"appliedFacets":{},"limit":N,"offset":0,"searchText":"flutter"}
# Dos trampas verificadas contra tableros reales:
#   1. el <site> del path CXS NO lleva el locale. `wday/cxs/rappi/es/Rappi_jobs`
#      responde 405; `wday/cxs/rappi/Rappi_jobs` responde 200.
#   2. el <tenant> no siempre es la primera etiqueta del host: en
#      "nvidia.wd5.myworkdayjobs.com" es "nvidia", y en "rappi.wd12…" es "rappi"
#      (el "wd12" es el subdominio numérico, no el tenant).
# `searchText` busca en título Y descripción (en NVIDIA "GeForce" → 47, "Pune" → 93),
# así que un solo POST con "flutter" ya es una señal fiable de ausencia o presencia.

WD_LOCALE_RE = re.compile(r"^([a-z]{2}(?:-[A-Za-z]{2,4})?)/")
WD_TENANT_SUBDOMAIN_RE = re.compile(r"^wd\d+$", re.I)
WORKDAY_LIMIT = 20


def workday_site(slug):
    """'es/Rappi_jobs' → ('Rappi_jobs', 'es');  'Rappi_jobs' → ('Rappi_jobs', '')."""
    m = WD_LOCALE_RE.match(slug or "")
    if m:
        return slug[m.end():], m.group(1)
    return slug or "", ""


def workday_tenants(host):
    """Candidatos de tenant a partir del host, en orden de probabilidad.

    Solo las etiquetas previas a `myworkdayjobs` son candidatas: las de la
    segunda etiqueta (`wd12`, `wd5`) son el subdominio del tenant, no el tenant.
    """
    labels = [l for l in (host or "").split(".") if l]
    if "myworkdayjobs" in labels:
        labels = labels[:labels.index("myworkdayjobs")]
    if not labels:
        return []
    real = [l for l in labels if not WD_TENANT_SUBDOMAIN_RE.match(l)]
    return real or labels[:1]


def workday_cxs_url(host, tenant, site):
    return f"https://{host}/wday/cxs/{tenant}/{site}/jobs"


def workday_fetch(host, slug, search="flutter", limit=WORKDAY_LIMIT, timeout=None):
    """Consulta el CXS de Workday. Devuelve el JSON parseado o None.

    Prueba cada tenant candidato hasta que uno responda. Un 405/422 con un tenant
    y 200 con otro es lo normal: el site existe pero el tenant no coincide.
    """
    site, _locale = workday_site(slug)
    if not host or not site:
        return None
    for tenant in workday_tenants(host):
        url = workday_cxs_url(host, tenant, site)
        raw = http_post_json(url, {"appliedFacets": {}, "limit": limit,
                                   "offset": 0, "searchText": search},
                             timeout=timeout)
        if raw.startswith("__") or raw == "__404__":
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "jobPostings" in data:
            return data
    return None


# ── Normalizadores por ATS ───────────────────────────────────────────

def to_iso_date(value):
    """Normaliza una fecha a YYYY-MM-DD.

    Greenhouse y Ashby ya devuelven ISO (basta truncar), pero Lever manda un
    Unix timestamp (sin convertirlo, `[:10]` devolvía "1790040082" en el informe
    en vez de una fecha) y Workday manda texto relativo ("Posted 13 Days Ago"),
    que hay que resolver contra hoy.
    """
    if value in (None, ""):
        return ""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return parse_relative_date(value)
    if n > 10_000_000_000:  # milisegundos
        n //= 1000
    try:
        return datetime.fromtimestamp(n, timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return ""


_REL_UNITS = {
    "today": 0, "hour": 0, "day": 1, "week": 7, "month": 30, "year": 365,
}


def parse_relative_date(text):
    """'Posted 13 Days Ago' → '2026-09-22'. Devuelve "" si no se puede resolver."""
    text = (text or "").strip()
    if not text:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):  # ya es ISO
        return text[:10]
    if re.fullmatch(r"\d+", text):  # epoch, por si llega como string
        return to_iso_date(int(text))
    m = re.search(r"(\d+)\W*([a-z]+)", text.lower())  # "30+ Days" → 30, days
    if not m:
        # "Posted Today" no lleva número: hoy es hoy.
        return datetime.now(timezone.utc).date().isoformat() if "today" in text.lower() else ""
    unidad = m.group(2).rstrip("s")  # "days" → "day"
    if unidad not in _REL_UNITS:
        return ""
    dias = int(m.group(1)) * _REL_UNITS[unidad]
    return (datetime.now(timezone.utc) - timedelta(days=dias)).date().isoformat()


def norm_greenhouse(data, slug=None):
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


def norm_ashby(data, slug=None):
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


def norm_lever(data, slug=None):
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
            "published": to_iso_date(j.get("createdAt")),
        })
    return out


def norm_workday(data, host, slug, matched="flutter"):
    """Normaliza el listado CXS de Workday.

    El listado no trae descripción (eso vive en un endpoint por vacante), pero
    el rol llegó aquí porque `searchText` encontró `matched` ("flutter"/"dart")
    en título o cuerpo. Se marca con `matched` para que `select_roles` lo cuente
    como Flutter/Dart confirmado aunque el título no lo diga (p. ej. "Mobile
    Engineer" cuya descripción menciona Flutter).
    """
    site, locale = workday_site(slug)
    # El path de navegación lleva locale; el de CXS no (ver workday_fetch).
    nav = f"{locale}/{site}" if locale else site
    out = []
    for j in (data.get("jobPostings") or []):
        ext = j.get("externalPath") or ""
        out.append({
            "title": (j.get("title") or "").strip(),
            "location": j.get("locationsText") or "",
            "url": f"https://{host}/{nav}{ext}" if ext else "",
            "description": "",  # solo en el endpoint de detalle, no se pide
            "published": to_iso_date(j.get("postedOn")),
            "matched": matched,
            "ref": (j.get("bulletFields") or [None])[0],
        })
    return out


def norm_workable(data, slug=None):
    """Widget público de Workable (apply.workable.com/api/v1/widget/...)."""
    out = []
    for j in (data.get("jobs") or []):
        loc = ", ".join(str(x) for x in (j.get("city"), j.get("state"), j.get("country")) if x)
        if not loc and j.get("telecommuting"):
            loc = "Remote"
        out.append({
            "title": (j.get("title") or "").strip(),
            "location": loc,
            "url": j.get("application_url") or j.get("url") or "",
            "description": strip_html(j.get("description") or "")[:400],
            "published": to_iso_date(j.get("published_on")),
        })
    return out


def norm_recruitee(data, slug=None):
    """API pública de Recruitee: https://{slug}.recruitee.com/api/offers/."""
    out = []
    for j in (data.get("offers") or []):
        loc = j.get("location") or ""
        if not loc:
            locs = j.get("locations") or []
            loc = (locs[0].get("name", "") if locs and isinstance(locs[0], dict) else "")
        if j.get("remote") and "remote" not in (loc or "").lower():
            loc = f"{loc} (Remote)".strip()
        out.append({
            "title": (j.get("title") or "").strip(),
            "location": loc,
            "url": j.get("careers_url") or j.get("careers_apply_url") or "",
            "description": strip_html(j.get("description") or "")[:400],
            "published": to_iso_date(j.get("published_at")),
        })
    return out


def norm_teamtailor(data, slug=None):
    """JSON Feed público de Teamtailor (https://{host}/jobs.json)."""
    out = []
    for j in (data.get("items") or []):
        jp = j.get("_jobposting") or {}
        loc = ""
        jl = jp.get("jobLocation")
        addrs = jl if isinstance(jl, list) else [jl]
        for item in addrs:
            if not isinstance(item, dict):
                continue
            addr = item.get("address") if isinstance(item.get("address"), dict) else item
            loc = ", ".join(str(addr.get(k)) for k in
                            ("addressLocality", "addressRegion", "addressCountry")
                            if isinstance(addr, dict) and addr.get(k))
            if loc:
                break
        if not loc and jp.get("jobLocationType"):
            loc = "Remote"
        out.append({
            "title": (j.get("title") or "").strip(),
            "location": loc,
            "url": j.get("url") or "",
            "description": strip_html(
                j.get("content_text") or j.get("content_html") or "")[:400],
            "published": to_iso_date(j.get("date_published")),
        })
    return out


def norm_smartrecruiters(data, slug=None):
    """Public Posting API de SmartRecruiters (limit 100 por página)."""
    out = []
    for j in (data.get("content") or []):
        loc = (j.get("location") or {}).get("fullLocation") or ""
        company = (j.get("company") or {}).get("identifier") or slug or ""
        url = (f"https://jobs.smartrecruiters.com/{company}/{j.get('id')}"
               if company and j.get("id") else "")
        out.append({
            "title": (j.get("name") or "").strip(),
            "location": loc,
            "url": url,
            "description": "",
            "published": to_iso_date(j.get("releasedDate")),
        })
    return out


def norm_bamboohr(data, slug=None):
    """BambooHR: https://{slug}.bamboohr.com/careers/list (Accept: JSON)."""
    out = []
    for j in (data.get("result") or []):
        loc = j.get("location") or {}
        if isinstance(loc, dict):
            loc = ", ".join(str(loc.get(k)) for k in ("city", "state") if loc.get(k))
        ats_loc = j.get("atsLocation") or {}
        if not loc and isinstance(ats_loc, dict):
            loc = ", ".join(str(ats_loc.get(k)) for k in
                            ("city", "state", "country") if ats_loc.get(k))
        if j.get("isRemote") or str(j.get("locationType")) == "1":
            loc = f"{loc} (Remote)".strip()
        jid = j.get("id")
        out.append({
            "title": (j.get("jobOpeningName") or "").strip(),
            "location": loc,
            "url": (f"https://{slug}.bamboohr.com/careers/{jid}"
                    if slug and jid else ""),
            "description": "",
            "published": "",
        })
    return out


def norm_personio(raw, slug=None):
    """Personio: feed XML público (jobs.personio.de|com/xml)."""
    out = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return out
    for p in root.findall("position"):
        def txt(tag):
            el = p.find(tag)
            return (el.text or "").strip() if el is not None else ""
        desc = " ".join((v.text or "").strip() for v in
                        p.findall("jobDescriptions/jobDescription/value"))
        jid = txt("id")
        out.append({
            "title": txt("name"),
            "location": txt("office"),
            "url": (f"https://{slug}.jobs.personio.de/job/{jid}"
                    if slug and jid else ""),
            "description": strip_html(desc)[:400],
            "published": to_iso_date(txt("createdAt")),
        })
    return out


NORMALIZERS = {
    "greenhouse": norm_greenhouse, "ashby": norm_ashby, "lever": norm_lever,
    "workable": norm_workable, "recruitee": norm_recruitee,
    "teamtailor": norm_teamtailor, "smartrecruiters": norm_smartrecruiters,
    "bamboohr": norm_bamboohr, "personio": norm_personio,
}


def board_urls(ats, slug):
    """URLs a probar para un tablero (Personio tiene dos dominios)."""
    urls = [ATS_PROBES[ats].format(slug=slug)]
    urls += [u.format(slug=slug) for u in ATS_URL_ALTS.get(ats, [])]
    return urls


def normalize_board(ats, data, slug):
    """Normaliza la respuesta del tablero, sea JSON (dict) o XML (str)."""
    return NORMALIZERS[ats](data, slug)


# ── Sondeo ───────────────────────────────────────────────────────────

def host_slugs(company):
    """Slugs plausibles a partir del dominio y del nombre.

    Para los tableros de subdominio (Recruitee, Personio, BambooHR, Workable)
    el slug coincide casi siempre con la primera etiqueta del dominio, así que
    probarlo no es "adivinar a ciegas": es el camino natural cuando /careers es
    una SPA y no expone ningún enlace al ATS.
    """
    domain = (company.get("domain") or "").strip().lower()
    domain = re.sub(r"^https?://", "", domain).split("/")[0]
    prefix = domain.split(".")[0] if domain else ""
    base = re.sub(r"[^a-z0-9]", "", normalize_company(company.get("name", "")))
    out = []
    for s in (prefix, base):
        if s and s not in out:
            out.append(s)
    return out[:2]


GENERIC_WORDS = {
    # Sufijos que no cambian de empresa: "Somnio" y "Somnio Software" son la
    # misma. Cualquier otra palabra extra ("Rows" vs "Rows Financial") se toma
    # como otra compañía y el tablero se descarta.
    "software", "technologies", "technology", "tech", "tecnologia", "tecnologias",
    "sistemas", "systems", "labs", "lab", "digital", "group", "grupo", "studio",
    "studios", "inc", "llc", "corp", "global", "latam", "com", "app", "mobile",
    "sa", "sas", "ltda", "brasil", "brazil", "colombia", "mexico", "chile",
    "argentina", "jobs", "careers", "beneficios", "servicos", "services",
}


def board_slug_plausible(ats, slug, company):
    """¿El identificador del tablero se parece al nombre/dominio de la empresa?

    Una página de carreras puede enlazar tableros que no son suyos (un partner,
    un footer): en la semilla real aparecieron `Etsy Labs → personio/code` y
    `Remote → greenhouse/zinier`, boards legítimos de otra empresa. Si el slug no
    se parece al nombre ni al dominio, el tablero no se acepta: es preferible
    dejarla `sin_tablero` (se reintenta en otra ronda) a llenar el informe con
    vacantes de un tercero.
    """
    if not slug:
        return False
    base = slug
    if ats.startswith("workday:"):
        base = ats.split(":", 1)[1].split(".")[0]
    elif ats == "teamtailor":
        partes = [p for p in slug.split(".")
                  if p not in ("www", "jobs", "careers", "teamtailor", "com",
                               "io", "net", "app")]
        base = partes[0] if partes else slug
    s = canon_name(base.split(".")[0])
    if not s:
        return False
    nombre = canon_name(company.get("name"))
    dominio = canon_name(canon_domain(company.get("domain")).split(".")[0])
    return bool((nombre and (s in nombre or nombre in s))
                or (dominio and (s in dominio or dominio in s)))


def board_matches_company(declarado, company_name):
    """¿El nombre que declara el tablero es el de esta empresa?

    Comparación estricta a propósito: los slugs globales salen del dominio y una
    palabra genérica puede ser el board de otro (`Remote` apuntando al tablero
    de un tercero). Se acepta el mismo nombre canónico o uno con sufijo
    corporativo; cualquier palabra extra descarta el tablero y se sigue probando.
    """
    a, b = canon_name(declarado), canon_name(company_name)
    if not a or not b:
        return True  # sin datos no se descarta por prejuicio
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    if long_.startswith(short):
        return long_[len(short):] in GENERIC_WORDS
    return False


class Prober:
    MAX_INTENTOS = 20  # por EMPRESA: 1 ruta de carreras + 2 slugs × (6 ATS de
    # subdominio + 3 globales). Con 14 el descubrimiento global no llegaba a
    # probarse en empresas que gastaban presupuesto en los ATS de subdominio.

    def __init__(self, verbose=False, slug_ciegos=False, host_directo=True):
        self.verbose = verbose
        # Path 4 (slugs a ciegas sobre los 3 grandes) sigue DESACTIVADO por
        # defecto: medido, rinde ~0% en LATAM (25 empresas LATAM → 0 tableros).
        # `host_directo` es distinto: solo prueba tableros cuyo host ES el de la
        # empresa (recruitee/personio/bamboohr/...), donde el slug sí correlaciona
        # con el dominio, y exige que el tablero devuelva roles.
        self.slug_ciegos = slug_ciegos
        self.host_directo = host_directo
        self.fallos = 0
        self.intentos = 0   # acumulado de toda la ronda (solo para el resumen)
        self._usados = 0    # consumido en la empresa actual (reinicia en probe)
        # De la última probe: de dónde salió el tablero y qué URL de carreras lo
        # reveló. `resolution` distingue un tablero verificado ("registro"),
        # deducido de la web ("careers") o de host directo ("host-directo").
        self.resolution = None
        self.last_careers_url = None

    def gastar(self):
        """Gasta una petición de la empresa actual. False si se agotó el presupuesto.

        El presupuesto es POR EMPRESA a propósito. Con un contador global el
        primer con 12 slugs agotaba la ronda entera y todas las empresas
        siguientes devolvían "sin tablero" sin llegar a hacer una sola petición
        (bug real: una ronda de 60 empresas solo sondeaba ~6).
        """
        if self._usados >= self.MAX_INTENTOS:
            return False
        self.intentos += 1
        self._usados += 1
        return True

    def get(self, url):
        if self.fallos >= EMPRESAS_FALLOS_MAX:
            return None
        raw = http_get(url)
        if raw == "__404__":
            return None  # slug inexistente: normal, no cuenta como fallo
        if raw == "__NET__":
            return None  # host muerto: tampoco es "nos bloquean"
        if raw.startswith("__ERR__"):
            self.fallos += 1
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _raw_board(self, ats, slug):
        """Descarga el primer endpoint que responda de un tablero."""
        for url in board_urls(ats, slug):
            if self.fallos >= EMPRESAS_FALLOS_MAX or not self.gastar():
                return None
            raw = http_get(url)
            if raw == "__404__" or raw == "__NET__":
                continue
            if raw.startswith("__ERR__"):
                self.fallos += 1
                continue
            return raw
        return None

    def board(self, ats, slug):
        """Sondea un tablero no-Workday. Devuelve (ats, slug, roles) o None.

        `roles == []` es una respuesta válida (tablero vacío) y se conserva: el
        llamador decide si es fiable (deducido de /careers) o no (host directo).
        """
        raw = self._raw_board(ats, slug)
        if raw is None:
            return None
        try:
            data = raw if ats == "personio" else json.loads(raw)
        except json.JSONDecodeError:
            return None
        return ats, slug, normalize_board(ats, data, slug)

    def workday(self, ats, slug, search="flutter"):
        """Sondea un tablero Workday. Devuelve (ats, slug, roles) o None."""
        host = ats.split(":", 1)[1] if ats.startswith("workday:") else ats
        if not self.gastar():
            return None
        data = workday_fetch(host, slug, search=search)
        if data is None:
            return None
        return ats, slug, norm_workday(data, host, slug, matched=search)

    def _board_name(self, ats, slug):
        """Nombre que declara el tablero, si el proveedor lo publica.

        Solo Greenhouse expone metadatos del board (`/v1/boards/{slug}`). Sirve
        para no dar por bueno un tablero global homónimo: el slug sale del
        dominio de la empresa, pero una palabra genérica puede pertenecer a otra
        compañía (el caso real fue `Remote` apuntando al board de un tercero).
        """
        if ats != "greenhouse" or not self.gastar():
            return None
        raw = http_get(f"https://boards-api.greenhouse.io/v1/boards/{slug}")
        if not raw or raw.startswith("__") or raw.startswith("__ERR__"):
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return (data.get("name") or "").strip() or None

    def probe_host_directo(self, company):
        """Prueba los ATS cuyo slug se deriva del nombre/dominio de la empresa.

        Es la respuesta a las webs de carreras que son una SPA (o están tras
        Cloudflare): no hace falta leer ningún HTML, se consulta directamente
        el identificador habitual de cada proveedor. Solo se acepta un tablero
        si devuelve ≥1 vacante, porque SmartRecruiters responde 200 con 0 para
        identificadores inexistentes.

        Cubre los dos mundos: los ATS de subdominio (Recruitee, Personio,
        BambooHR, Workable, Teamtailor) y los globales (Greenhouse, Ashby,
        Lever) con el slug natural. Estos últimos parecían "adivinar a ciegas",
        pero el slug es el prefijo del dominio de la empresa, no una palabra
        inventada: así apareció `greenhouse/quintoandar` (110 vacantes) en una
        empresa cuya web no enlaza ningún tablero.
        """
        if not self.host_directo:
            return None
        slugs = host_slugs(company)
        if not slugs:
            return None
        for cand in slugs:
            for ats in ("workable", "recruitee", "bamboohr", "teamtailor",
                        "smartrecruiters", "personio",
                        "greenhouse", "ashby", "lever"):
                if self.fallos >= EMPRESAS_FALLOS_MAX:
                    return None
                slug = f"{cand}.teamtailor.com" if ats == "teamtailor" else cand
                if self.verbose:
                    print(f"    · {company['name']} → {ats}/{slug} (host directo)")
                hit = self.board(ats, slug)
                if hit and hit[2]:
                    if ats == "greenhouse":
                        declarado = self._board_name(ats, slug)
                        if declarado and not board_matches_company(
                                declarado, company.get("name")):
                            if self.verbose:
                                print(f"      ✗ {ats}/{slug}: es '{declarado}', "
                                      f"no {company['name']}")
                            continue
                    if self.verbose:
                        print(f"      ✓ {ats}/{slug}: {len(hit[2])} roles")
                    self.resolution = "host-directo"
                    return hit
        return None

    def probe(self, company):
        """Devuelve (ats, slug, roles) para la primera fuente que responda.

        Orden: (1) ats/slug ya conocidos, (2) deducidos de la página de carreras,
        (3) tablero en el host natural de la empresa, (4) slugs a ciegas (opt-in).

        Deja en `self.resolution` de dónde salió el tablero ("registro",
        "careers", "host-directo" o "ciego") y en `self.last_careers_url` la
        página que lo reveló. Importa porque un tablero vacío deducido de la
        página de la empresa es fiable ("no hay vacantes"), mientras que uno
        adivinado vacío casi siempre es slug equivocado.
        """
        self._usados = 0  # el presupuesto de peticiones es por empresa
        self.resolution = None
        self.last_careers_url = None
        known_ats = company.get("ats") or ""

        # 1) Ya resuelto en el registro.
        if company.get("slug"):
            if known_ats.startswith("workday:"):
                hit = self.workday(known_ats, company["slug"])
                if hit:
                    self.resolution = "registro"
                    if self.verbose:
                        print(f"    · {company['name']} → {known_ats}/{company['slug']}: "
                              f"{len(hit[2])} roles")
                    return hit
            elif known_ats in ATS_PROBES:
                hit = self.board(known_ats, company["slug"])
                if hit:
                    self.resolution = "registro"
                    return hit

        # 2) Deducir de la página de carreras (sigue siendo el paso más fiable).
        #    Si la empresa no trae `careers_url`, se deduce del dominio.
        if self.gastar():
            ats, slug, careers = resolve_board(company)
            self.last_careers_url = careers
            if ats and not board_slug_plausible(ats, slug, company):
                # La página enlaza un tablero que no es de esta empresa.
                if self.verbose:
                    print(f"    ✗ {company['name']}: {ats}/{slug} no se parece a "
                          f"la empresa (descartado)")
                ats, slug = None, None
            if ats:
                self.resolution = "careers"
            if self.verbose and ats:
                print(f"    · {company['name']} → {ats}/{slug} (deducido de {careers})")
            if ats and ats.startswith("workday:"):
                hit = self.workday(ats, slug)
                if hit:
                    if self.verbose:
                        print(f"      ✓ {ats}/{slug}: {len(hit[2])} roles")
                    return hit
                # Todos los tenants fallaron: se reintenta con "dart" por si el
                # tablero usa otra palabra, antes de rendirse con este tablero.
                hit = self.workday(ats, slug, search="dart")
                if hit:
                    if self.verbose:
                        print(f"      ✓ {ats}/{slug}: {len(hit[2])} roles (buscando dart)")
                    return hit
            elif ats in ATS_PROBES:
                hit = self.board(ats, slug)
                if hit:
                    if self.verbose:
                        print(f"      ✓ {ats}/{slug}: {len(hit[2])} roles")
                    return hit
                time.sleep(EMPRESAS_PAUSA_S)

        # 3) Host natural de la empresa (SPA/Cloudflare en /careers).
        hit = self.probe_host_directo(company)
        if hit:
            return hit

        # 4) Slugs candidatos a ciegas (opt-in: ver Prober.slug_ciegos).
        vacios = None
        if not self.slug_ciegos:
            return None, None, []
        for slug in slug_candidates(company):
            for ats, url_tpl in ATS_PROBES.items():
                if self.fallos >= EMPRESAS_FALLOS_MAX or not self.gastar():
                    # Un tablero que respondió vacío puede ser slug equivocado
                    # (p. ej. greenhouse/nubank existe pero Nubank usa otro):
                    # se reporta, pero nunca como "la empresa no tiene vacantes".
                    return vacios or (None, None, [])
                blind = f"{slug}.teamtailor.com" if ats == "teamtailor" else slug
                if self.verbose:
                    print(f"    · {company['name']} → {ats}/{blind}")
                hit = self.board(ats, blind)
                if hit is None:
                    time.sleep(EMPRESAS_PAUSA_S)
                    continue
                if not hit[2]:
                    if vacios is None:
                        vacios = hit
                    time.sleep(EMPRESAS_PAUSA_S)
                    continue
                if self.verbose:
                    print(f"      ✓ {ats}/{blind}: {len(hit[2])} roles")
                self.resolution = "ciego"
                return hit
        if vacios:
            self.resolution = "ciego"
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


# Un puesto presencial en un país que no es LATAM no es aplicable: no se puede
# postular desde Venezuela. El score lo "^penalizaba" pero igual salía en el
# informe y acababa siendo ruido (India, EE.UU. presencial, etc.).
NON_LATAM_COUNTRY_RE = re.compile(
    r"\b(india|pakistan|bangladesh|china|taiwan|japan|korea|israel|australia|"
    r"new zealand|south africa|poland|ukraine|romania|hungary|island|ireland|"
    r"netherlands|germany|france|spain|portugal|italy|sweden|norway|denmark|"
    r"finland|belgium|austria|switzerland|czech|turkey|egypt|saudi|emirates|"
    r"nigeria|kenya|ghana|vietnam|philippines|indonesia|malaysia|thailand|"
    r"singapore|canada|estados unidos|united states|usa)\b", re.I)


def es_aplicable(role, company):
    """False cuando el puesto no es alcanzable desde LATAM.

    Descarta solo lo inequívoco: una ciudad/país explícito que no es LATAM y
    sin ninguna señal de remoto. Si el tablero no dice nada, no se descarta
    (preferimos un falso positivo a perder una vacante real).
    """
    blob = f"{role.get('title','')} {role.get('location','')} {role.get('description','')}"
    if REMOTE_RE.search(blob):
        return True
    if LATAM_RE.search(blob):
        return True
    return not NON_LATAM_COUNTRY_RE.search(blob)


def select_roles(roles, company):
    """Quedate con los roles relevantes: Flutter/Dart explícito, o móvil para revisar.

    Tres filtros, en este orden:
      1. stack      — Flutter/Dart en el título, o `matched` (el searchText del
                      board lo confirmó en el cuerpo aunque el título no lo diga).
      2. Review     — móvil + Flutter en la descripción: se marca ⚠ para mirar.
      3. Aplicable  — descartable si es presencial en un país que no es LATAM.
    """
    picked = []
    for r in roles:
        title = r.get("title", "")
        desc = r.get("description", "")
        # `matched` solo vale si el término de búsqueda era Flutter o Dart: un
        # "mobile" que vino del searchText NO confirma el stack.
        matched = r.get("matched") in ("flutter", "dart")
        if has_flutter_dart(title) or matched:
            r["review"] = False
        elif MOBILE_RE.search(title) and has_flutter_dart(desc):
            r["review"] = True
        else:
            continue
        if not es_aplicable(r, company):
            continue
        r["score"] = score_role(r, company)
        picked.append(r)
    return sorted(picked, key=lambda x: -x["score"])


# ── Informe ──────────────────────────────────────────────────────────

def fmt_report(hits, date_str, time_str, checked, errs):
    nuevas = sum(1 for h in hits for r in h["roles"] if r.get("_nueva"))
    lines = [
        f"# Empresas Flutter con vacantes - {date_str}\n",
        f"> 🔎 Sondeo de tableros de empresa · {time_str} UTC · "
        f"{len(hits)} empresas con vacantes Flutter de {checked} sondeadas\n",
    ]
    if nuevas:
        lines.append(f"> 🆕 {nuevas} vacante(s) no vista(s) antes en esta ronda\n")
    lines.append("> 📍 Prioridad: empresas LATAM que contratan LATAM, luego EE.UU. remote-first\n")
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
        for n, r in enumerate(h["roles"], 1):
            flag = " ⚠ **verificar:** solo Flutter en la descripción" if r.get("review") else ""
            nueva = "🆕 " if r.get("_nueva") else ""
            lines.append(f"### {n}. {nueva}{r['title']} _(score {r['score']})_")
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
    # Índices de lo ya conocido: clave, nombre canónico y dominio canónico. Sin
    # esto, la poda de `verificar_registro` se deshacía en la ronda siguiente:
    # el alta volvía a meter "Serasa Experian" junto a "Serasa" porque solo se
    # comparaba la clave normalizada.
    keys = {k for k in registry["companies"]}
    # canon_name → región: la similitud de nombres solo vale dentro de la misma
    # región, porque "Patagonia" (US) y "Patagonia IT" (LATAM) son otra empresa.
    names = {}
    for c in registry["companies"].values():
        n = canon_name(c.get("name"))
        if n:
            names.setdefault(n, c.get("region"))
    domains = {canon_domain(c.get("domain")) for c in registry["companies"].values()}
    domains.discard("")
    for it in items:
        name = (it.get("nombre") or it.get("empresa") or it.get("name") or "").strip()
        if not name:
            continue
        key = normalize_company(name)
        if not key or key in keys:
            continue
        domain = it.get("dominio") or it.get("domain") or it.get("website") or ""
        if domain.startswith("http"):
            domain = re.sub(r"^https?://(www\.)?", "", domain).split("/")[0]
        loc = it.get("location") or it.get("ubicacion") or ""
        region = "us" if re.search(r"united states|estados unidos|\busa\b|\bcanada\b",
                                   loc, re.I) else "latam"
        cname, cdom = canon_name(name), canon_domain(domain)
        if cdom and cdom in domains:
            continue  # mismo dominio con otro nombre: no se duplica
        if any(n == cname or (names_similar(cname, n)
                              and names[n] in (None, region))
               for n in names):
            continue  # misma empresa con otra grafía: no se duplica
        stack = " ".join(str(t) for t in (it.get("tech_stack") or []))
        usa_flutter = "flutter" in stack.lower() or "dart" in stack.lower()
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
        keys.add(key)
        if cname:
            names.setdefault(cname, region)
        if cdom:
            domains.add(cdom)
    return added


# ── Main ─────────────────────────────────────────────────────────────

def encolar_roles(company, roles):
    """Añade las vacantes a estado/cola_aplicaciones.json (dedup por URL).

    La cola es la puerta de entrada de `cv-apply`: dejarlas ahí convierte el
    informe en trabajo accionable sin tener que copiar URLs a mano. No envía
    nada; el envío sigue siendo manual por el reCAPTCHA de los ATS.
    """
    if not roles:
        return 0
    try:
        from cola_aplicaciones import Cola
    except Exception as exc:  # la cola es opcional: no debe romper la ronda
        print(f"[cola] no disponible: {exc}")
        return 0
    cola = Cola()
    n = 0
    for r in roles:
        url = (r.get("url") or "").strip()
        if not url:
            continue
        try:
            _, nuevo = cola.add(
                url, r.get("title", ""), company.get("name", ""),
                ubicacion=r.get("location", ""), fuente="empresa",
            )
            n += int(nuevo)
        except ValueError:
            continue
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=60, help="Máximo de empresas a sondear")
    ap.add_argument("--company", help="Sondea solo una empresa (nombre o clave)")
    ap.add_argument("--refresh", action="store_true", help="Ignora la cache")
    ap.add_argument("--dry-run", action="store_true", help="No escribe NADA (ni registro, ni cache, ni .md)")
    ap.add_argument("--stats", action="store_true", help="Resumen del registro y sale")
    ap.add_argument("--verbose", action="store_true", help="Muestra cada sondeo")
    ap.add_argument("--min-score", type=int, default=0, dest="min_score",
                    help="Descarta roles con score menor a este valor (0 = sin filtro)")
    ap.add_argument("--slugs-ciegos", action="store_true", dest="slugs_ciegos",
                    help="Prueba slugs adivinados si falla la página de carreras "
                         "(~0%% de acierto en LATAM, pero cada empresa cuesta ~10 "
                         "peticiones: úsalo solo para una empresa concreta)")
    ap.add_argument("--host-directo", action=argparse.BooleanOptionalAction,
                    dest="host_directo", default=True,
                    help="Prueba el tablero en el host natural de la empresa "
                         "(Recruitee/Personio/BambooHR/Workable/Teamtailor). "
                         "Activado por defecto; --no-host-directo lo desactiva")
    ap.add_argument("--nuevas", action="store_true",
                    help="Emite solo vacantes no vistas antes (delta de la ronda)")
    ap.add_argument("--no-encolar", action="store_false", dest="encolar",
                    default=True, help="No añadir las vacantes a cola_aplicaciones.json")
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
        # Prioridad: sin sondear > sin tablero > resto; Tier 1 LATAM primero y,
        # dentro del grupo, la que lleva más tiempo sin revisarse. Las entradas
        # sin dominio no se pueden sondear: van al final (se marcan sin_dominio).
        def prioridad(c):
            rank = {"nuevo": 0, "sin_tablero": 1, "tablero_vacio": 2,
                    "con_vacante": 3, "sin_vacante_flutter": 4,
                    "sin_dominio": 9}.get(c.get("status"), 5)
            return (rank,
                    c.get("tier", 9) if isinstance(c.get("tier"), int) else 9,
                    0 if c.get("region") == "latam" else 1,
                    c.get("last_checked") or "")

        pool = [c for c in companies.values()
                if c.get("domain") or c.get("ats") or c.get("status") != "sin_dominio"]
        targets = sorted(pool, key=prioridad)[: args.limit]

    cache = load_json(EMPRESAS_CACHE_PATH, {})
    hits, errs, checked, skipped, encoladas = [], [], 0, 0, 0

    hist = Historial() if not args.dry_run else None

    def _probe(company, cached):
        """Sondea una empresa. Cada una lleva su propio `Prober`.

        El Prober acumula estado (presupuesto de peticiones, fallos, resolución),
        así que no se comparte entre hilos: uno por empresa deja el sondeo en
        paralelo sin carreras y el presupuesto sigue siendo por empresa.
        """
        if not args.refresh and cache_is_fresh(cached):
            # Copia: el scoring y el delta escriben en los roles y no queremos
            # que esos campos acaben guardados en la cache.
            return {"ats": cached["ats"], "slug": cached["slug"],
                    "roles": copy.deepcopy(cached["roles"]), "cached": True}
        prober = Prober(verbose=args.verbose, slug_ciegos=args.slugs_ciegos,
                        host_directo=args.host_directo)
        ats, slug, roles = prober.probe(company)
        time.sleep(EMPRESAS_PAUSA_S)  # cortesía: ni en paralelo van en ráfaga
        return {"ats": ats, "slug": slug, "roles": roles, "cached": False}

    def _persist(aviso=False):
        """Guarda registro, cache e historial (parcial durante la ronda).

        Antes solo se escribía al final: una ronda de 60 empresas que se cortaba
        a mitad (timeout, Ctrl-C) perdía TODO el trabajo y el informe no existía.
        """
        if args.dry_run:
            return
        registry["updated"] = date_str
        save_json(EMPRESAS_REGISTRY_PATH, registry)
        save_json(EMPRESAS_CACHE_PATH, cache)
        if hist:
            hist.save()
        if aviso:
            # stderr: stdout es el canal máquina que parsea el orquestador
            # (`[parcial] 20/60` se leía como si fuese la ruta del informe).
            print(f"[parcial] {procesadas}/{len(targets)} empresas sondeadas",
                  file=sys.stderr, flush=True)

    procesadas = 0
    workers = max(1, min(EMPRESAS_WORKERS, len(targets)))
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futuros = [pool.submit(_probe, c, cache.get(c["key"])) for c in targets]
            # Se itera en el orden de `targets` (no en orden de llegada) para que
            # el informe y el historial queden deterministas entre rondas.
            for fut, c in zip(futuros, targets):
                try:
                    res = fut.result()
                except Exception as exc:  # una empresa caída no tumba la ronda
                    errs.append(f"{c['name']}: error {exc}")
                    continue
                procesadas += 1
                key = c["key"]
                ats, slug, roles = res["ats"], res["slug"], res["roles"]
                if not res["cached"]:
                    checked += 1
                    if ats and not args.dry_run:
                        cache[key] = {"ts": now.isoformat(timespec="seconds"),
                                      "ats": ats, "slug": slug, "roles": roles}

                if not ats:
                    sin_dominio = not c.get("domain")
                    errs.append(f"{c['name']}: " + (
                        "sin dominio (no se puede sondear)" if sin_dominio
                        else "sin tablero localizado"))
                    if not args.dry_run:
                        c["last_checked"] = now.isoformat(timespec="seconds")
                        if sin_dominio:
                            c["status"] = "sin_dominio"
                        elif c.get("status") in (None, "nuevo", "sin_tablero", "sin_dominio"):
                            # No se degrada una empresa que ayer sí tenía tablero: un
                            # fallo puntual de red no es "ha cerrado su tablero".
                            c["status"] = "sin_tablero"
                    continue

                selected = select_roles(roles, c)
                if args.min_score:
                    selected = [r for r in selected if r["score"] >= args.min_score]
                if args.verbose and selected:
                    descartados = len(select_roles(roles, c)) - len(selected)
                    if descartados:
                        print(f"      ✗ {c['name']}: {descartados} roles bajo "
                              f"--min-score {args.min_score}")
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

                # Delta: comparar con el historial central. `_nueva` marca lo que no se
                # había visto nunca; con --nuevas el informe emite solo eso.
                nuevas = []
                for r in selected:
                    vkey = vacancy_key(c["name"], r["title"])
                    prev = hist.get(CATEGORY, vkey) if hist else None
                    r["_nueva"] = prev is None
                    if prev is None:
                        nuevas.append(r)
                    elif not (prev.get("fecha_visto") or "").startswith(date_str):
                        skipped += 1

                report_roles = nuevas if args.nuevas else selected
                if not report_roles:
                    if not args.dry_run and procesadas % 10 == 0:
                        _persist(aviso=True)
                    continue

                best = max(r["score"] for r in report_roles)
                hits.append({"company": c, "ats": ats, "slug": slug,
                             "roles": report_roles, "score": best})

                # Auto-encolar en la cola de aplicaciones (dedup por URL). No envía
                # nada: deja el trabajo listo para `cv-apply`.
                if args.encolar and not args.dry_run and selected:
                    encoladas += encolar_roles(c, selected)

                # Historial: añade las no vistas (o refresca las de hoy).
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

                if not args.dry_run and procesadas % 10 == 0:
                    _persist(aviso=True)
    finally:
        # También con Ctrl-C o timeout: lo sondeado hasta aquí queda guardado.
        _persist()

    if not args.dry_run:
        os.makedirs(OUT_DIR, exist_ok=True)
        out_path = os.path.join(OUT_DIR, f"{date_str}-empresas-vacantes.md")
        # Ronda sin novedades con `--nuevas`: no se pisa el informe del día con
        # un "sin resultados", que borraría lo encontrado hace un rato (la
        # vacante sigue en la cola y en el historial, pero el .md es la prueba
        # que lee el humano).
        if args.nuevas and not hits and os.path.exists(out_path):
            print(f"[sin novedades] se conserva {out_path}", file=sys.stderr)
        else:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(fmt_report(hits, date_str, time_str, checked, errs))
        print(out_path)
    else:
        print("[dry-run] no se escribió registro, cache, historial ni informe")
        print(fmt_report(hits, date_str, time_str, checked, errs))

    print("---JOBCOUNT---")
    print(sum(len(h["roles"]) for h in hits))
    print("---NUEVAS---")
    print(sum(1 for h in hits for r in h["roles"] if r.get("_nueva")))
    print("---ENCOLADAS---")
    print(encoladas)
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
