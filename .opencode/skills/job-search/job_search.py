#!/usr/bin/env python3
"""job_search.py — Flutter/LATAM remote job aggregator.

Orquestra 9 fuentes, filtra, deduplica, normaliza salarios
y genera markdown en resultados/vacantes/{YYYY-MM-DD}.md
"""

import html
import json
import os
import re
import sys
import traceback
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
TIMEOUT = 20
LATAM_COUNTRIES = {
    "argentina", "bolivia", "brazil", "chile", "colombia", "costa rica",
    "cuba", "dominican republic", "ecuador", "el salvador", "guatemala",
    "honduras", "mexico", "nicaragua", "panama", "paraguay", "peru",
    "uruguay", "venezuela",
}
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
OUTPUT_DIR = os.path.join(PROJECT_DIR, "resultados", "vacantes")


# ── helpers ──────────────────────────────────────────────────────────

def fetch(url, fmt="text"):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = r.read().decode("utf-8", errors="replace")
            return data
    except Exception as e:
        return f"__FETCH_ERR__:{e}"


def is_latam_remote(loc_restrictions, desc=""):
    if not loc_restrictions:
        return True
    locs = {l.lower().strip() for l in loc_restrictions}
    if locs & LATAM_COUNTRIES:
        return True
    if "latam" in desc.lower() or "latin america" in desc.lower():
        return True
    return False


def has_flutter_dart(title, desc=""):
    if re.search(r'\bflutter\b', title.lower()) or re.search(r'\bdart\b', title.lower()):
        return True
    desc_short = desc[:300].lower()
    return bool(re.search(r'\bflutter\b', desc_short)) or bool(re.search(r'\bdart\b', desc_short))


def normalize_company(c):
    c = c.lower().strip()
    c = re.sub(r'[^\w\s]', '', c)
    c = re.sub(r'\s+', ' ', c)
    for suffix in [', inc', ', llc', ', s.a', ', s.a.s', ', s.a.c', ', c.a',
                   ' inc', ' llc', ' s.a', ' corp', ' ltd', ' s de rl',
                   ' s.a. de c.v.', ', s.a. de c.v.', ' sa de cv', ', sa de cv']:
        if c.endswith(suffix):
            c = c[:-len(suffix)].strip()
    return c


def normalize_title(t):
    t = t.lower().strip()
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def dedup_key(job):
    return normalize_company(job.get("company", "")) + "::" + normalize_title(job.get("title", ""))


def merge_jobs(existing, new):
    if not existing:
        return new
    for k in ["salary_min", "salary_max", "salary_currency", "url", "source"]:
        if not existing.get(k) and new.get(k):
            existing[k] = new[k]
    if not existing.get("description") and new.get("description"):
        existing["description"] = new["description"]
    existing["sources"] = list(set(existing.get("sources", [existing.get("source", "")]) + [new.get("source", "")]))
    return existing


SALARY_TO_USD = {
    "USD": 1, "US$": 1, "$": 1,
    "MXN": 0.055, "MX$": 0.055,
    "COP": 0.00024,
    "BRL": 0.19,
    "ARS": 0.0011,
    "CLP": 0.0011,
    "PEN": 0.27,
    "VES": 0.000027,
    "EUR": 1.08,
    "PLN": 0.25,
    "GBP": 1.27,
}


def salary_to_usd_per_month(val, currency):
    if not val:
        return None
    currency = currency.upper() if currency else "USD"
    rate = SALARY_TO_USD.get(currency, 1)
    return round(val * rate, 0)


def parse_salary_text(text):
    if not text:
        return None, None, None
    nums = re.findall(r'[\d.,]+', text.replace(',', ''))
    if not nums:
        return None, None, None
    vals = [float(n) for n in nums if n.replace('.', '').isdigit()]
    if not vals:
        return None, None, None
    cur = "USD"
    for c in ["$", "US$", "MX$", "EUR", "PLN", "GBP", "MXN", "BRL", "COP"]:
        if c in text:
            cur = c
            break
    if len(vals) >= 2:
        return min(vals), max(vals), cur
    return vals[0], None, cur


# ── Source parsers ───────────────────────────────────────────────────

# LinkedIn devuelve matches difusos (keyword=Flutter) cuyo título NO menciona
# Flutter/Dart. Se mantienen los roles mobile/software marcándolos para
# revisión ("⚠ verificar"); se descarta ruido claramente ajeno.
LI_NOISE = re.compile(
    r"\b(delphi|cto|chief|socio|sócio|low[- ]?code|data analyst|data engineer|"
    r"devops|designer|wordpress|salesforce|recruiter|java( developer)?|nodejs|"
    r"\.net|python|machine learning|analytics|\bai\b|\bhr\b|react( native)?|"
    r"on-site|onsite|\bbanco\b|banking|back office|administra|tesorero)\b",
    re.I,
)
LI_MOBILE = re.compile(
    r"(mobile|móvil|movil|flutter|dart|android|ios|\bapp\b|desenvolvimento|"
    r"develop|\bdeveloper\b|engineer|fullstack|full-stack|frontend|front-end|"
    r"backend|software|programador|dev\b)", re.I,
)


def parse_linkedin(html_text):
    jobs = []
    cards = re.findall(
        r'<a class="base-card__full-link[^"]*"\s*href="([^"]+)".*?'
        r'base-search-card__title[^>]*>\s*([^<]+).*?'
        r'base-search-card__subtitle[^>]*>(?:.*?<a[^>]*>\s*)?([^<]+).*?'
        r'job-search-card__location[^>]*>\s*([^<]+).*?'
        r'(?:job-search-card__listdate[^>]*>([^<]+)|listdate--new[^>]*>([^<]+))',
        html_text, re.DOTALL
    )
    for m in cards:
        url, title, company, loc, date1, date2 = m
        title = title.strip()
        company = company.strip()
        loc = loc.strip()
        time_text = (date1 or date2 or "").strip()
        if has_flutter_dart(title):
            review = False
        elif LI_NOISE.search(title):
            continue
        elif not LI_MOBILE.search(title):
            continue
        else:
            review = True
        if "hour" not in time_text.lower() and "day" not in time_text.lower():
            if "23" not in time_text and "17" not in time_text and "19" not in time_text:
                continue
        jobs.append({
            "source": "LinkedIn",
            "title": title,
            "company": company,
            "location": loc,
            "url": url.split("?")[0],
            "time": time_text,
            "modality": "Remoto",
            "review": review,
            "salary_min": None, "salary_max": None, "salary_currency": None,
            "description": "",
        })
    return jobs


def parse_getonboard(text):
    jobs = []
    try:
        data = json.loads(text)
    except Exception:
        return jobs
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        title = attrs.get("title", "")
        desc = (attrs.get("description_headline") or "") + " " + (attrs.get("description") or "")
        if not has_flutter_dart(title, desc):
            continue
        company = ""
        if "company" in attrs and isinstance(attrs["company"], dict):
            cd = attrs["company"].get("data", {})
            if cd:
                company = str(cd.get("id", ""))
        remote = attrs.get("remote", False)
        modality = "Remoto" if remote else "⚠ No especificada"
        salary_min = attrs.get("min_salary")
        salary_max = attrs.get("max_salary")
        currency = "USD"
        pub_ts = attrs.get("published_at", 0)
        if pub_ts:
            pub_date = datetime.fromtimestamp(pub_ts, tz=timezone.utc).strftime("%Y-%m-%d")
        else:
            pub_date = ""
        url = item.get("links", {}).get("public_url", "")
        jobs.append({
            "source": "GetOnBoard",
            "title": title,
            "company": company or "No especificada",
            "location": "Remote",
            "url": url,
            "time": pub_date,
            "modality": modality,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": currency,
            "description": desc[:500],
        })
    return jobs


def parse_himalayas(text):
    jobs = []
    try:
        data = json.loads(text)
    except Exception:
        return jobs
    for item in data.get("jobs", []):
        title = item.get("title", "")
        desc = item.get("description", "") or ""
        if not has_flutter_dart(title, desc):
            continue
        cats = [c.lower() for c in item.get("categories", [])]
        parent_cats = [c.lower() for c in item.get("parentCategories", [])]
        if not ("engineering" in " ".join(cats + parent_cats).lower()
                or "mobile" in " ".join(cats + parent_cats).lower()
                or "flutter" in " ".join(cats + parent_cats).lower()):
            if not has_flutter_dart(title):
                continue
        loc_restrictions = item.get("locationRestrictions", [])
        if not is_latam_remote(loc_restrictions, desc):
            if "latam" not in desc.lower() and "latin america" not in desc.lower():
                continue
        pub_ts = item.get("pubDate", 0)
        if pub_ts:
            pub_date = datetime.fromtimestamp(pub_ts, tz=timezone.utc).strftime("%Y-%m-%d")
        else:
            pub_date = ""
        sal_min = item.get("minSalary")
        sal_max = item.get("maxSalary")
        currency = item.get("currency")
        seniority = ", ".join(item.get("seniority", []))
        company = item.get("companyName", "")
        url = item.get("guid") or item.get("applicationLink") or ""
        mod = "Remoto"
        employment = item.get("employmentType", "")
        jobs.append({
            "source": "Himalayas",
            "title": title,
            "company": company,
            "location": ", ".join(loc_restrictions) if loc_restrictions else "Worldwide",
            "url": url,
            "time": pub_date,
            "modality": mod,
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_currency": currency,
            "seniority": seniority,
            "employment_type": employment,
            "description": desc[:500],
        })
    return jobs


def parse_remotejobs(text):
    jobs = []
    try:
        data = json.loads(text)
    except Exception:
        return jobs
    for item in data.get("data", []):
        title = item.get("title", "")
        desc = item.get("description", "") or ""
        if not has_flutter_dart(title, desc):
            continue
        company = ""
        if isinstance(item.get("company"), dict):
            company = item["company"].get("name", "")
        location = item.get("location", "Remote")
        url = item.get("url", "")
        posted = item.get("posted_at", "")[:10]
        sal_min = item.get("salary_min")
        sal_max = item.get("salary_max")
        jtype = item.get("type", "")
        jobs.append({
            "source": "RemoteJobs.org",
            "title": title,
            "company": company,
            "location": location,
            "url": url,
            "time": posted,
            "modality": jtype,
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_currency": None,
            "description": desc[:500],
        })
    return jobs


def parse_jobicy(text):
    jobs = []
    try:
        data = json.loads(text)
    except Exception:
        return jobs
    if not data.get("success") or not data.get("jobs"):
        return jobs
    for item in data["jobs"]:
        title = item.get("jobTitle", "")
        desc = item.get("jobDescription", "") or item.get("jobExcerpt", "") or ""
        if not has_flutter_dart(title, desc):
            continue
        geo = item.get("jobGeo", "")
        url = item.get("url", "")
        company = item.get("companyName", "")
        sal_min = item.get("salaryMin")
        sal_max = item.get("salaryMax")
        sal_cur = item.get("salaryCurrency", "USD")
        pub_date = item.get("pubDate", "")[:10]
        level = item.get("jobLevel", "")
        industry = item.get("jobIndustry", [])
        jobs.append({
            "source": "Jobicy",
            "title": title,
            "company": company,
            "location": geo,
            "url": url,
            "time": pub_date,
            "modality": "Remoto",
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_currency": sal_cur,
            "seniority": level,
            "industry": ", ".join(industry) if industry else "",
            "description": desc[:500],
        })
    return jobs


def parse_careernest(text):
    jobs = []
    try:
        data = json.loads(text)
    except Exception:
        return jobs
    for item in data.get("jobs", []):
        title = item.get("title", "")
        desc = item.get("description", "") or ""
        if not has_flutter_dart(title, desc):
            continue
        company = item.get("company", "")
        location = item.get("location", "")
        job_type = item.get("job_type", "")
        url = item.get("job_url", "")
        posted = item.get("posted_at", "")[:10]
        sal = item.get("salary", {}) or {}
        sal_min = sal.get("min")
        sal_max = sal.get("max")
        sal_cur = sal.get("currency", "USD")
        jobs.append({
            "source": "Career Nest",
            "title": title,
            "company": company,
            "location": location,
            "url": url,
            "time": posted,
            "modality": job_type,
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_currency": sal_cur,
            "description": desc[:500],
        })
    return jobs


class ComputrabajoParser(HTMLParser):
    """Stupid-simple parser that finds job cards by scanning text blocks."""

    def __init__(self):
        super().__init__()
        self.offers = []
        self._current = {}
        self._in_article = False
        self._tag_stack = []
        self._text_buf = []
        self._article_count = 0

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag == "article" and "box_offer" in ad.get("class", ""):
            self._in_article = True
            self._current = {"id": ad.get("data-id", "")}
            self._text_buf = []
        if self._in_article:
            self._tag_stack.append(tag)
            if tag == "a" and "t_ellipsis" in ad.get("class", ""):
                self._current["link"] = ad.get("href", "")

    def handle_endtag(self, tag):
        if self._in_article and self._tag_stack:
            self._tag_stack.pop()
        if tag == "article" and self._in_article:
            self._in_article = False
            self._finish_offer()

    def handle_data(self, data):
        if self._in_article:
            self._text_buf.append(data.strip())

    def _finish_offer(self):
        text = " ".join(t for t in self._text_buf if t)
        lines = [t.strip() for t in text.replace("&#xED;", "í")
                 .replace("&#xE1;", "á").replace("&#xF3;", "ó")
                 .replace("&#xFA;", "ú").replace("&#xF1;", "ñ")
                 .replace("&#xE9;", "é").replace("&amp;", "&")
                 .split() if t.strip()]
        title = ""
        company = ""
        location = ""
        salary = ""
        modality = ""
        date = ""
        for line in lines:
            ln = html.unescape(line)
            if not title and len(ln) > 5 and not any(
                    kw in ln.lower() for kw in ["postulado", "vista", "empleo",
                                                 "destacado", "urgente", "guardar",
                                                 "postular", "denunciar", "ocultar",
                                                 "mostrar", "favorito"]):
                title = ln
            if "remoto" in ln.lower() or "presencial" in ln.lower() or "híbrido" in ln.lower() or "hibrido" in ln.lower():
                modality = ln
            if "$" in ln:
                salary = ln
            if "hace" in ln.lower():
                date = ln
            if len(lines) > 3 and not company:
                potential_companies = [l for l in lines if len(l) > 4
                                       and not any(kw in l.lower() for kw in
                                                   ["hace", "día", "semana", "mes", "$",
                                                    "remoto", "presencial", "híbrido",
                                                    "postular", "guardar", "denunciar"])
                                       and l != title]
                if potential_companies:
                    company = potential_companies[0]
        if not has_flutter_dart(title):
            return
        full_url = self._current.get("link", "")
        self.offers.append({
            "title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "modality": modality,
            "date": date,
            "url": full_url,
        })


def parse_computrabajo(html_text, country):
    parser = ComputrabajoParser()
    try:
        parser.feed(html_text)
    except Exception:
        return []
    jobs = []
    for o in parser.offers:
        modality = "⚠ No especificada"
        if o["modality"]:
            ml = o["modality"].lower()
            if "remoto" in ml and "presencial" not in ml:
                modality = "Remoto"
            elif "remoto" in ml and "presencial" in ml:
                modality = "Híbrido"
            elif "presencial" in ml:
                modality = "Presencial"
        if country != "VE" and modality not in ("Remoto", "⚠ No especificada"):
            continue
        sal_min, sal_max, cur = parse_salary_text(o["salary"])
        jobs.append({
            "source": f"Computrabajo {country}",
            "title": o["title"],
            "company": o["company"] or "No especificada",
            "location": f"{o['location']}, {country_name(country)}" if o.get("location") else country_name(country),
            "url": o["url"],
            "time": o["date"],
            "modality": modality,
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_currency": cur,
            "description": "",
        })
    return jobs


def country_name(code):
    return {"VE": "Venezuela", "MX": "México", "CO": "Colombia",
            "AR": "Argentina", "CL": "Chile", "PE": "Perú",
            "EC": "Ecuador"}.get(code, code)


def parse_ct_title_from_url(url, country):
    """Parse job title and location from Computrabajo offer URL path."""
    path = url.lower()
    title = ""
    location = ""
    m = re.search(r'/oferta-de-trabajo-de-(.+?)-en-([^/]+)', path)
    if m:
        raw = m.group(1)
        loc_raw = m.group(2)
        # Strip trailing UUID hash from location
        loc_raw = re.sub(r'-[a-f0-9]{32,}$', '', loc_raw, flags=re.I)
        loc_raw = re.sub(r'[a-f0-9]{32,}$', '', loc_raw, flags=re.I)
        # Convert slug to readable text
        title = raw.replace('-', ' ').strip()
        location = loc_raw.replace('-', ' ').strip()
        # Capitalize words
        title = title.title()
        location = location.title()
    if not location:
        location = country_name(country)
    return title, location


def parse_ct_modality_from_url(url):
    if "hibrido" in url or "híbrido" in url:
        return "Híbrido"
    if "remoto" in url or "remota" in url:
        return "Remoto"
    if "presencial" in url:
        return "Presencial"
    return ""


def parse_computrabajo_ld(html_text, country):
    """Parse Computrabajo search page using JSON-LD data."""
    jobs = []
    scripts = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html_text, re.DOTALL
    )
    for s in scripts:
        try:
            data = json.loads(s)
        except Exception:
            continue
        for g in data.get("@graph", []):
            items = g.get("itemListElement", [])
            for item in items:
                url = item.get("url", "")
                if not url:
                    continue
                title, location = parse_ct_title_from_url(url, country)
                if not has_flutter_dart(title):
                    continue
                modality = parse_ct_modality_from_url(url)
                if country != "VE" and modality == "Presencial":
                    continue
                if country != "VE" and modality == "Híbrido":
                    continue
                if not modality:
                    modality = "⚠ No especificada"
                # Determine company from URL if available (legacy path format)
                company = "No especificada"
                cm = re.search(r'/empresas/ofertas-de-trabajo-de-(.+?)--', url)
                if cm:
                    company = cm.group(1).replace('-', ' ').strip().title()
                jobs.append({
                    "source": f"Computrabajo {country}",
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": url,
                    "time": "",
                    "modality": modality,
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                    "description": "",
                })
    return jobs


def parse_remotico(html_text):
    """Remotico.io listing (/jobs/skill/flutter|dart): tarjetas SSR."""
    jobs = []
    pat = re.compile(
        r'<a href="(/jobs/[a-z0-9\-]+)" class="block".*?'
        r'<span class="relative">([^<]*)</span></h3></a>'
        r'<p class="text-xs[^"]*">([^<]*)</p>.*?'
        r'<span class="shrink-0[^"]*"[^>]*>([^<]*)</span>',
        re.DOTALL,
    )
    for m in pat.finditer(html_text):
        slug, title, company, time_text = m.groups()
        title = html.unescape(title.strip())
        company = html.unescape(company.strip())
        time_text = html.unescape(time_text.strip())
        if not title:
            continue
        jobs.append({
            "source": "Remotico",
            "title": title,
            "company": company or "No especificada",
            "location": "Remoto",
            "url": "https://remotico.io" + slug,
            "time": time_text,
            "modality": "Remoto",
            "salary_min": None, "salary_max": None, "salary_currency": None,
            "description": "",
        })
    return jobs


def enrich_remotico(jobs, max_fetch=12):
    """Enrich Remotico jobs with JSON-LD JobPosting (company, países, fecha)."""
    enriched = 0
    for j in jobs:
        if enriched >= max_fetch:
            break
        raw = fetch(j.get("url", ""))
        if raw.startswith("__FETCH_ERR__"):
            continue
        for s in re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            raw, re.DOTALL
        ):
            try:
                data = json.loads(s)
            except Exception:
                continue
            if not (isinstance(data, dict) and data.get("@type") == "JobPosting"):
                continue
            org = data.get("hiringOrganization") or {}
            if isinstance(org, dict) and org.get("name"):
                j["company"] = org["name"].strip()
            posted = data.get("datePosted", "")
            if posted:
                try:
                    d = datetime.fromisoformat(posted.replace("Z", "+00:00"))
                    days = int((datetime.now(timezone.utc) - d).total_seconds() // 86400)
                    j["time"] = f"hace {days} días" if days > 0 else "hoy"
                except Exception:
                    pass
            countries = []
            for c in data.get("applicantLocationRequirements", []) or []:
                if isinstance(c, dict) and c.get("name"):
                    countries.append(c["name"])
            if countries:
                j["location"] = "Remoto · " + ", ".join(countries)
            salary = data.get("baseSalary") or {}
            if isinstance(salary, dict):
                val = salary.get("value")
                if isinstance(val, dict):
                    smin = val.get("minValue") or val.get("value")
                    smax = val.get("maxValue")
                    cur = salary.get("currency") or val.get("currency")
                    if smin:
                        j["salary_min"] = smin
                        j["salary_max"] = smax
                        j["salary_currency"] = (cur or "USD").upper()
            enriched += 1
            break
    return jobs


def _rss_text(value):
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def _workremoto_reltime(pubdate):
    try:
        d = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %z")
    except Exception:
        return ""
    delta = datetime.now(timezone.utc) - d
    days = delta.days
    if days <= 0:
        return f"hace {max(int(delta.total_seconds() // 3600), 0)} h"
    return f"hace {days} días"


WR_COUNTRY = re.compile(
    r"\b(argentina|bolivia|chile|colombia|costa rica|ecuador|el salvador|"
    r"españ[ao]|espana|guatemala|honduras|méxico|mexico|nicaragua|panamá|"
    r"paraguay|perú|peru|uruguay|venezuela|brasil|república dominicana|"
    r"dominican)\b", re.I,
)


def parse_workremoto(xml_text):
    """Workremoto.com RSS de categoría (desarrollo): título, link, fecha, desc."""
    jobs = []
    items = re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL)
    for it in items:
        m_title = re.search(r"<title>(.*?)</title>", it, re.DOTALL)
        m_link = re.search(r"<link>(.*?)</link>", it, re.DOTALL)
        m_pub = re.search(r"<pubDate>(.*?)</pubDate>", it, re.DOTALL)
        m_desc = re.search(r"<description>(.*?)</description>", it, re.DOTALL)
        title = _rss_text(m_title.group(1) if m_title else "")
        desc = _rss_text(m_desc.group(1) if m_desc else "")
        link = (m_link.group(1) if m_link else "").strip()
        if not title or not has_flutter_dart(title, desc):
            continue
        company = "No especificada"
        found = re.search(r"([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ.\- ]{2,40}) busca", desc)
        if found:
            company = found.group(1).strip()
        loc = "Remoto"
        m = WR_COUNTRY.search(link)
        if m:
            loc = f"Remoto ({m.group(1).title()})"
        jobs.append({
            "source": "Workremoto",
            "title": re.sub(r"[\s]*–[\s]*Remoto$", "", title, flags=re.I),
            "company": company,
            "location": loc,
            "url": link,
            "time": _workremoto_reltime(m_pub.group(1) if m_pub else ""),
            "modality": "Remoto",
            "salary_min": None, "salary_max": None, "salary_currency": None,
            "description": desc[:300],
        })
    return jobs


def _normalize_salary_period(smin, smax, source=""):
    """Detect if salary values are annual and convert to monthly."""
    if source == "RemoteJobs.org":
        vals = [v for v in [smin, smax] if v]
        if vals and all(v > 30000 for v in vals):
            return tuple(round(v / 12) if v else v for v in [smin, smax])
    return smin, smax


def salary_str(job):
    smin = job.get("salary_min")
    smax = job.get("salary_max")
    cur = job.get("salary_currency") or "USD"
    src = job.get("source", "")
    smin, smax = _normalize_salary_period(smin, smax, src)
    if smin and smax:
        usd_min = salary_to_usd_per_month(smin, cur)
        usd_max = salary_to_usd_per_month(smax, cur)
        if cur == "USD" or not usd_min:
            return f"${smin:,.0f} - ${smax:,.0f}/mes"
        else:
            return f"{smin:,.0f} {cur} (~${usd_min:,.0f} - ${usd_max:,.0f} USD/mes)"
    elif smin:
        usd = salary_to_usd_per_month(smin, cur)
        if cur == "USD" or not usd:
            return f"${smin:,.0f}/mes"
        else:
            return f"{smin:,.0f} {cur} (~${usd:,.0f} USD/mes)"
    return ""


# ── Main ─────────────────────────────────────────────────────────────

SOURCES_LINKEDIN = [  # noqa: N816
    ("Flutter", "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Flutter&f_WT=2&f_TPR=r86400&location=Latin%20America&start={page}",
     "html", parse_linkedin, 1),
    ("Flutter Developer (exacto)", "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=%22Flutter%20Developer%22&f_WT=2&f_TPR=r86400&location=Latin%20America&start={page}",
     "html", parse_linkedin, 1),
    ("Dart", "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Dart&f_WT=2&f_TPR=r86400&location=Latin%20America&start={page}",
     "html", parse_linkedin, 1),
]
SOURCES_GETONBOARD = [
    ("GetOnBoard", "https://www.getonbrd.com/api/v0/search/jobs?query=flutter&remote=true&per_page=20",
     "text", parse_getonboard),
]
SOURCES_HIMALAYAS = [
    ("Himalayas", "https://himalayas.app/jobs/api/search?q=flutter&sort=recent&offset={page}",
     "text", parse_himalayas, 3),
]
SOURCES_REMOTEJOBS = [
    ("RemoteJobs.org", "https://remotejobs.org/api/v1/jobs?q=flutter&category=programming&limit=50",
     "text", parse_remotejobs),
]
SOURCES_CAREERNEST = [
    ("Career Nest", "https://careernest.cloud/api/feed?category=software-development&type=remote&limit=50",
     "text", parse_careernest),
]
SOURCES_JOBICY = [
    ("Jobicy (flutter)", "https://jobicy.com/api/v2/remote-jobs?count=50&tag=flutter", "text", parse_jobicy),
    ("Jobicy (mobile)", "https://jobicy.com/api/v2/remote-jobs?count=50&tag=mobile", "text", parse_jobicy),
]
SOURCES_COMPUTRABAJO = [
    ("VE", "https://ve.computrabajo.com/trabajo-de-flutter", parse_computrabajo_ld),
    ("MX", "https://mx.computrabajo.com/trabajo-de-flutter", parse_computrabajo_ld),
    ("CO", "https://co.computrabajo.com/trabajo-de-flutter", parse_computrabajo_ld),
    ("AR", "https://ar.computrabajo.com/trabajo-de-flutter", parse_computrabajo_ld),
    ("CL", "https://cl.computrabajo.com/trabajo-de-flutter", parse_computrabajo_ld),
    ("PE", "https://pe.computrabajo.com/trabajo-de-flutter", parse_computrabajo_ld),
    ("EC", "https://ec.computrabajo.com/trabajo-de-flutter", parse_computrabajo_ld),
]
SOURCES_REMOTICO = [
    ("Remotico (flutter)", "https://remotico.io/jobs/skill/flutter", "html", parse_remotico),
    ("Remotico (dart)", "https://remotico.io/jobs/skill/dart", "html", parse_remotico),
]
SOURCES_WORKREMOTO = [
    ("Workremoto (desarrollo)", "https://workremoto.com/categoria-empleo/desarrollo/feed/", "text", parse_workremoto),
]


def fetch_source(name, url, fmt, parser, pages=1):
    all_jobs = []
    for p in range(pages):
        u = url.format(page=p * 10) if pages > 1 else url
        raw = fetch(u)
        if raw.startswith("__FETCH_ERR__"):
            return [], raw.split(":", 1)[1] if ":" in raw else raw
        if fmt == "text":
            jobs = parser(raw)
        else:
            jobs = parser(raw)
        all_jobs.extend(jobs)
        if len(jobs) == 0:
            break
    return all_jobs, None


def fmt_section(name, jobs, extra=""):
    if not jobs:
        return f"## {name} (0 vacantes)\n\n> Sin resultados\n"
    lines = [f"## {name} ({len(jobs)} vacantes{extra})\n"]
    for i, j in enumerate(jobs, 1):
        sal = salary_str(j)
        lines.append(f"### {i}. {j['title']}")
        lines.append(f"**Empresa:** {j.get('company', 'N/A')}")
        lines.append(f"**Ubicación:** {j.get('location', 'N/A')} | **Modalidad:** {j.get('modality', 'N/A')}")
        parts = []
        if j.get("time"):
            parts.append(f"**⏰** {j['time']}")
        if sal:
            parts.append(f"**💰** {sal}")
        if j.get("seniority"):
            parts.append(f"**Seniority:** {j['seniority']}")
        if parts:
            lines.append(" | ".join(parts))
        url = j.get("url", "")
        if url:
            lines.append(f"**🔗** [{j.get('source', 'Link')}]({url})")
        if j.get("review"):
            lines.append("> ⚠ **verificar:** el título no menciona Flutter/Dart (match difuso de LinkedIn); revisa el aviso antes de aplicar.")
        lines.append("`[Aplicar con cv-apply]`\n")
    return "\n".join(lines)


def fmt_computrabajo_section(source_name, jobs):
    if not jobs:
        return f"### {source_name} (0 vacantes)\n> Sin resultados\n"
    lines = [f"### {source_name} ({len(jobs)} vacantes)"]
    for i, j in enumerate(jobs, 1):
        sal = salary_str(j)
        lines.append(f"\n### {i}. {j['title']}")
        lines.append(f"**Empresa:** {j.get('company', 'N/A')}")
        lines.append(f"**Ubicación:** {j.get('location', 'N/A')} | **Modalidad:** {j.get('modality', 'N/A')}")
        parts = []
        if j.get("time"):
            parts.append(f"**⏰** {j['time']}")
        if sal:
            parts.append(f"**💰** {sal}")
        if parts:
            lines.append(" | ".join(parts))
        url = j.get("url", "")
        if url:
            lines.append(f"**🔗** [Computrabajo]({url})")
        lines.append("`[Aplicar con cv-apply]`")
    return "\n".join(lines)


def enrich_ct_company(url):
    """Fetch individual CT job page to get company name from JSON-LD."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=8) as r:
            html = r.read().decode("utf-8", errors="replace")
        scripts = re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        for s in scripts:
            data = json.loads(s)
            for g in data.get("@graph", []):
                if g.get("@type") == "JobPosting":
                    org = g.get("hiringOrganization", {})
                    if isinstance(org, dict) and org.get("name"):
                        return org["name"].strip()
    except Exception:
        pass
    return ""


def enrich_ct_jobs(jobs, max_fetch=8):
    """Enrich Computrabajo jobs with company names from individual pages."""
    enriched = 0
    for j in jobs:
        if j.get("company") and j["company"] != "No especificada":
            continue
        if enriched >= max_fetch:
            break
        company = enrich_ct_company(j.get("url", ""))
        if company:
            j["company"] = company
            enriched += 1
    return jobs


def fmt_section_ct(name, jobs, extra=""):
    return "\n".join([f"## {name}\n"] +
                     [fmt_computrabajo_section(f"{cname}", jobs[cname]) for cname in sorted(jobs.keys())])


def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    all_jobs = []
    source_errors = []
    source_counts = {}
    total_sources = 9

    # 1. LinkedIn (3 queries precisas, hasta 2 páginas por query)
    li_jobs_raw = []
    for li_name, li_url, _fmt, _parser, _pages in SOURCES_LINKEDIN:
        for p in range(2):
            url = li_url.format(page=p * 10)
            raw = fetch(url)
            if raw.startswith("__FETCH_ERR__"):
                source_errors.append(f"LinkedIn ({li_name} page {p}): {raw.split(':',1)[1] if ':' in raw else raw}")
                break
            j = _parser(raw)
            li_jobs_raw.extend(j)
            if len(j) < 10:
                break
    all_jobs.extend(li_jobs_raw)
    source_counts["LinkedIn"] = len(li_jobs_raw)

    # 2. GetOnBoard
    jobs, err = fetch_source(*SOURCES_GETONBOARD[0][:4])
    if err:
        source_errors.append(f"GetOnBoard: {err}")
    all_jobs.extend(jobs)
    source_counts["GetOnBoard"] = len(jobs)

    # 3. Himalayas
    him_jobs = []
    for p in range(3):
        url = SOURCES_HIMALAYAS[0][1].format(page=p * 20)
        raw = fetch(url)
        if raw.startswith("__FETCH_ERR__"):
            source_errors.append(f"Himalayas (page {p}): {raw.split(':',1)[1] if ':' in raw else raw}")
            break
        j = SOURCES_HIMALAYAS[0][3](raw)
        him_jobs.extend(j)
        if len(j) < 20:
            break
    all_jobs.extend(him_jobs)
    source_counts["Himalayas"] = len(him_jobs)

    # 4. RemoteJobs.org
    jobs, err = fetch_source(*SOURCES_REMOTEJOBS[0][:4])
    if err:
        source_errors.append(f"RemoteJobs.org: {err}")
    all_jobs.extend(jobs)
    source_counts["RemoteJobs.org"] = len(jobs)

    # 5. Career Nest (with fallback)
    raw = fetch(SOURCES_CAREERNEST[0][1])
    if raw.startswith("__FETCH_ERR__"):
        source_errors.append(f"Career Nest: {raw.split(':',1)[1] if ':' in raw else raw}")
        source_counts["Career Nest"] = 0
    else:
        jobs = SOURCES_CAREERNEST[0][3](raw)
        all_jobs.extend(jobs)
        source_counts["Career Nest"] = len(jobs)

    # 6. Jobicy (multiple tags)
    jb_jobs = []
    for name, url, fmt, parser in SOURCES_JOBICY:
        raw = fetch(url)
        if raw.startswith("__FETCH_ERR__"):
            continue
        jobs = parser(raw)
        jb_jobs.extend(jobs)
    all_jobs.extend(jb_jobs)
    source_counts["Jobicy"] = len(jb_jobs)

    # 7. Computrabajo
    ct_by_country = defaultdict(list)
    for country, url, parser in SOURCES_COMPUTRABAJO:
        raw = fetch(url)
        if raw.startswith("__FETCH_ERR__"):
            source_errors.append(f"Computrabajo {country}: {raw.split(':',1)[1] if ':' in raw else raw}")
            if "403" in raw:
                continue
            continue
        # Try JSON-LD parser first, fall back to HTML parser
        jobs = parse_computrabajo_ld(raw, country)
        if not jobs:
            jobs = parse_computrabajo(raw, country)
        # Enrich with company names from individual pages
        jobs = enrich_ct_jobs(jobs, max_fetch=6)
        for j in jobs:
            all_jobs.append(j)
        ct_by_country[country].extend(jobs)
    source_counts["Computrabajo"] = sum(len(v) for v in ct_by_country.values())

    # 8. Remotico (HTML SSR + enrich JSON-LD JobPosting)
    re_jobs = []
    for _name, url, _fmt, parser in SOURCES_REMOTICO:
        raw = fetch(url)
        if raw.startswith("__FETCH_ERR__"):
            source_errors.append(f"{_name}: {raw.split(':',1)[1] if ':' in raw else raw}")
            continue
        re_jobs.extend(parser(raw))
    re_jobs = enrich_remotico(re_jobs, max_fetch=12)
    all_jobs.extend(re_jobs)
    source_counts["Remotico"] = len(re_jobs)

    # 9. Workremoto (RSS)
    wr_jobs = []
    for _name, url, _fmt, parser in SOURCES_WORKREMOTO:
        raw = fetch(url)
        if raw.startswith("__FETCH_ERR__"):
            source_errors.append(f"{_name}: {raw.split(':',1)[1] if ':' in raw else raw}")
            continue
        wr_jobs.extend(parser(raw))
    all_jobs.extend(wr_jobs)
    source_counts["Workremoto"] = len(wr_jobs)

    # ── Deduplicate ──
    seen = {}
    deduped = []
    for j in all_jobs:
        key = dedup_key(j)
        if key in seen:
            seen[key] = merge_jobs(seen[key], j)
        else:
            seen[key] = dict(j)
            deduped.append(seen[key])

    # ── Cross-session dedup vs estado/historial.json ──
    # No repetir vacantes ya listadas en ejecuciones anteriores.
    skipped = 0
    try:
        from tracker import Historial, vacancy_key
        hist = Historial()
        fresh = []
        skipped = 0
        for j in deduped:
            key = vacancy_key(j.get("company", ""), j.get("title", ""))
            prev = hist.get("vacantes", key)
            # Solo omite lo listado en días anteriores; lo del mismo día se re-lista
            # (la ejecución del día regenera el archivo con la vista completa).
            seen_today = bool(prev) and (prev.get("fecha_visto") or "").startswith(date_str)
            hist.add("vacantes", key, meta={
                "empresa": j.get("company", ""),
                "titulo": j.get("title", ""),
                "url": j.get("url", ""),
                "fuente": j.get("source", ""),
                "salario": j.get("salary_min"),
            })
            if not prev or seen_today:
                fresh.append(j)
            else:
                skipped += 1
        deduped = fresh
    except Exception:
        # Si no hay historial, se comporta como antes (sin dedup entre sesiones)
        traceback.print_exc()

    # Re-count per source after dedup
    source_counts_deduped = defaultdict(int)
    for j in deduped:
        src = j.get("source", "Unknown")
        source_counts_deduped[src] += 1

    # ── Build markdown ──
    sections = []
    sections.append(f"# Vacantes Flutter - {date_str}\n")
    sections.append(f"> 🎯 Buscador automático · {time_str} UTC · {total_sources} fuentes consultadas")
    sections.append("> 📍 Remoto LATAM (+ Venezuela presencial/híbrido)")
    if skipped:
        sections.append(f"> 🔁 {len(deduped)} nuevas · {skipped} ya vistas (historial central)\n")
    else:
        sections.append("")

    # LinkedIn
    li_jobs = [j for j in deduped if j.get("source") == "LinkedIn"]
    sections.append(f"---\n")
    sections.append(fmt_section("LinkedIn", li_jobs, " · ≤24h"))

    # GetOnBoard
    gob_jobs = [j for j in deduped if j.get("source") == "GetOnBoard"]
    sections.append(f"---\n")
    sections.append(fmt_section("GetOnBoard", gob_jobs))

    # Himalayas
    him_jobs_f = [j for j in deduped if j.get("source") == "Himalayas"]
    sections.append(f"---\n")
    sections.append(fmt_section("Himalayas", him_jobs_f))

    # RemoteJobs
    rj_jobs = [j for j in deduped if j.get("source") == "RemoteJobs.org"]
    sections.append(f"---\n")
    sections.append(fmt_section("RemoteJobs.org", rj_jobs))

    # Jobicy
    jb_jobs_f = [j for j in deduped if j.get("source") == "Jobicy"]
    sections.append(f"---\n")
    sections.append(fmt_section("Jobicy", jb_jobs_f))

    # Career Nest
    cn_jobs = [j for j in deduped if j.get("source") == "Career Nest"]
    sections.append(f"---\n")
    if cn_jobs:
        sections.append(fmt_section("Career Nest", cn_jobs))
    else:
        cn_errs = [e for e in source_errors if "Career Nest" in e]
        err_msg = cn_errs[0] if cn_errs else "No disponible temporalmente"
        sections.append(f"## Career Nest (0 vacantes)\n\n> Error: {err_msg}\n")

    # Computrabajo by country
    ct_jobs = defaultdict(list)
    for j in deduped:
        src = j.get("source", "")
        if src.startswith("Computrabajo"):
            ct_jobs[src.replace("Computrabajo ", "")].append(j)

    sections.append(f"---\n")
    sections.append(f"## Computrabajo\n")
    for ccode in ["VE", "MX", "CO", "PE", "AR", "CL", "EC"]:
        cname = country_name(ccode)
        extra = ""
        if ccode == "VE":
            extra = " · todas las modalidades"
        elif ccode in ("MX", "CO", "PE", "AR", "CL", "EC"):
            extra = " · solo remoto"
        if ct_jobs.get(ccode):
            sections.append(fmt_computrabajo_section(f"{cname}{extra}", ct_jobs[ccode]))
        else:
            sections.append(f"### {cname} (0 vacantes)\n> Sin resultados\n")

    # Remotico
    re_jobs_f = [j for j in deduped if j.get("source") == "Remotico"]
    sections.append(f"---\n")
    sections.append(fmt_section("Remotico", re_jobs_f))

    # Workremoto
    wr_jobs_f = [j for j in deduped if j.get("source") == "Workremoto"]
    sections.append(f"---\n")
    sections.append(fmt_section("Workremoto", wr_jobs_f))

    if source_errors:
        sections.append(f"---\n")
        sections.append(f"## Notas\n")
        for e in source_errors:
            sections.append(f"- ⚠ {e}")

    sections.append(f"\n---\n")
    sections.append("> 📝 Para aplicar: copia el 🔗 link y dímelo con \"aplica a esta vacante\" para generar CV personalizado con `cv-apply`.\n")

    markdown = "\n".join(sections)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{date_str}.md")

    if not deduped and os.path.exists(out_path):
        # Nada nuevo hoy y ya existe informe del día: no sobrescribir la lista que ya tiene.
        print(out_path + " (sin cambios, informe del día ya existe)")
        print("---JOBCOUNT---")
        print(len(deduped))
        print("---SKIPPED---")
        print(skipped)
        print("---SOURCES---")
        for k, v in sorted(source_counts_deduped.items()):
            print(f"{k}: {v}")
        print("---ERRORS---")
        for e in source_errors:
            print(e)
        return

    with open(out_path, "w") as f:
        f.write(markdown)

    print(out_path)
    print("---JOBCOUNT---")
    print(len(deduped))
    print("---SKIPPED---")
    print(skipped)
    print("---SOURCES---")
    for k, v in sorted(source_counts_deduped.items()):
        print(f"{k}: {v}")
    print("---ERRORS---")
    for e in source_errors:
        print(e)


if __name__ == "__main__":
    main()
