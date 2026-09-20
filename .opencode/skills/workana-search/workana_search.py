#!/usr/bin/env python3
"""workana_search.py — Buscador de proyectos mobile en Workana.

Scrapea la categoría IT & Programming > Mobile Development,
extrae el JSON embebido en el HTML y genera un markdown con todos
los proyectos, marcando con ✅ los que mencionan Flutter/Dart.

Output: resultados/vacantes-workana/{YYYY-MM-DD}.md
"""

import html
import json
import os
import re
import sys
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
TIMEOUT = 25
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
OUTPUT_DIR = os.path.join(PROJECT_DIR, "resultados", "vacantes-workana")

BASE_URL = "https://www.workana.com/jobs?category=it-programming&subcategory=mobile-development&page={page}"

MAX_PAGES = 20

FLUTTER_KEYWORDS = ["flutter", "dart", "cross-platform", "multiplataforma"]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None


def extract_results_initials(html_text):
    """Extract the JSON inside :results-initials='...' prop on <search> element."""
    m = re.search(
        r':results-initials=\'((?:[^\'\\]|\\.)*)\'',
        html_text, re.DOTALL
    )
    if not m:
        m = re.search(
            r':results-initials="((?:[^"\\]|\\.)*)"',
            html_text, re.DOTALL
        )
    if not m:
        return None
    raw = m.group(1)
    raw = raw.replace("\\'", "'")
    raw = raw.replace('\\"', '"')
    raw = raw.replace("\\/", "/")
    raw = raw.replace("\\n", "\n")
    raw = raw.replace("\\t", "\t")
    raw = html.unescape(raw)
    raw = re.sub(r'[\x00-\x1f]', '', raw)
    return raw


def has_flutter(job):
    title = (job.get("title") or "").lower()
    title_text = re.sub(r'<[^>]+>', '', title)
    for kw in FLUTTER_KEYWORDS:
        if kw in title_text:
            return True
    skills = job.get("skills") or []
    for s in skills:
        st = (s.get("anchorText") or "").lower()
        for kw in FLUTTER_KEYWORDS:
            if kw in st:
                return True
    return False


def parse_job_slug(job):
    slug = job.get("slug", "")
    return slug


def parse_budget(job):
    budget = job.get("budget", "")
    if not budget:
        return ""
    return budget.strip()


def parse_posted_date(job):
    return (job.get("postedDate") or "").strip()


def parse_skills(job):
    skills = job.get("skills") or []
    return [s.get("anchorText", "") for s in skills if s.get("anchorText")]


def strip_html(text):
    return re.sub(r'<[^>]+>', '', text).strip()


def truncate(text, max_len=200):
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    all_jobs = []
    total_count = 0
    pages_fetched = 0
    errors = []

    for page in range(1, MAX_PAGES + 1):
        url = BASE_URL.format(page=page)
        raw = fetch(url)
        if raw is None:
            errors.append(f"Page {page}: fetch error")
            break

        json_str = extract_results_initials(raw)
        if not json_str:
            errors.append(f"Page {page}: no results-initials found")
            break

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            errors.append(f"Page {page}: JSON decode error: {e}")
            break

        results = data.get("results", [])
        pagination = data.get("pagination", {})

        if not results:
            break

        for job in results:
            all_jobs.append({
                "slug": parse_job_slug(job),
                "title": strip_html(job.get("title", "")),
                "author": job.get("authorName", ""),
                "budget": parse_budget(job),
                "posted": parse_posted_date(job),
                "skills": parse_skills(job),
                "is_urgent": job.get("isUrgent", False),
                "is_hourly": job.get("isHourly", False),
                "is_flutter": has_flutter(job),
                "description": truncate(strip_html(job.get("description", ""))),
                "url": f"https://www.workana.com/job/{parse_job_slug(job)}" if parse_job_slug(job) else "",
            })

        total_count = pagination.get("total", 0)
        pages_fetched += 1

        current_page = pagination.get("page", page)
        total_pages = pagination.get("pages", 1)

        if current_page >= total_pages:
            break

    flutter_count = sum(1 for j in all_jobs if j["is_flutter"])

    # ── Cross-session dedup vs estado/historial.json ──
    # No repetir proyectos ya listados en ejecuciones anteriores.
    skipped = 0
    try:
        from tracker import Historial
        hist = Historial()
        fresh = []
        for j in all_jobs:
            key = j.get("slug") or f"workana::{j.get('title', '')}"
            is_new = hist.add("proyectos_workana", key, meta={
                "titulo": j.get("title", ""),
                "url": j.get("url", ""),
                "author": j.get("author", ""),
                "budget": j.get("budget"),
                "is_flutter": j.get("is_flutter"),
            })
            if is_new:
                fresh.append(j)
            else:
                skipped += 1
        all_jobs = fresh
    except Exception:
        traceback.print_exc()

    flutter_count = sum(1 for j in all_jobs if j["is_flutter"])

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{date_str}.md")

    lines = []
    lines.append(f"# Workana - Proyectos Mobile - {date_str}\n")
    lines.append(f"> Buscador automático · {time_str} UTC")
    lines.append(f"> {len(all_jobs)} proyectos nuevos ({pages_fetched} páginas) · {flutter_count} con Flutter/Dart ✅")
    if skipped:
        lines.append(f"> 🔁 {skipped} ya vistos omitidos (historial central)\n")

    if errors:
        lines.append("### Notas")
        for e in errors:
            lines.append(f"- ⚠ {e}")
        lines.append("")

    lines.append("---\n")
    lines.append(f"## Proyectos ({len(all_jobs)})\n")

    if not all_jobs:
        lines.append("> No se encontraron proyectos.\n")
    else:
        for i, j in enumerate(all_jobs, 1):
            badge = " ✅" if j["is_flutter"] else ""
            urgent = " 🔥 URGENTE" if j["is_urgent"] else ""
            hourly = " ⏱ Por hora" if j["is_hourly"] else ""
            title_line = f"### {i}.{badge}{urgent} {j['title']}{hourly}"
            lines.append(title_line)

            author = j["author"] or "No especificado"
            budget = j["budget"] or "No especificado"
            lines.append(f"**Cliente:** {author} | **Presupuesto:** {budget}")

            posted = j["posted"] or "No especificado"
            lines.append(f"**Publicado:** {posted}")

            if j["skills"]:
                skills_str = ", ".join(j["skills"])
                lines.append(f"**Habilidades:** {skills_str}")

            if j["description"]:
                lines.append(f"_{j['description']}_")

            if j["url"]:
                lines.append(f"🔗 [{j['url']}]({j['url']})")

            lines.append("`[Aplicar con cv-apply]`\n")

    markdown = "\n".join(lines)

    if not all_jobs and os.path.exists(out_path):
        # Nada nuevo hoy y ya existe informe del día: no sobrescribir la lista que ya tiene.
        print(out_path + " (sin cambios, informe del día ya existe)")
        print("---JOBCOUNT---")
        print(len(all_jobs))
        print("---SKIPPED---")
        print(skipped)
        print("---SOURCES---")
        print(f"Total: {len(all_jobs)}")
        print(f"Flutter/Dart: {flutter_count}")
        print(f"Páginas: {pages_fetched}")
        print("---ERRORS---")
        for e in errors:
            print(e)
        return

    with open(out_path, "w") as f:
        f.write(markdown)

    print(out_path)
    print("---JOBCOUNT---")
    print(len(all_jobs))
    print("---SKIPPED---")
    print(skipped)
    print("---SOURCES---")
    print(f"Total: {len(all_jobs)}")
    print(f"Flutter/Dart: {flutter_count}")
    print(f"Páginas: {pages_fetched}")
    print("---ERRORS---")
    for e in errors:
        print(e)


if __name__ == "__main__":
    main()
