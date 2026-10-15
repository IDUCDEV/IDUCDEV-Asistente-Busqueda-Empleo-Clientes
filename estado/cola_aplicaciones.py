#!/usr/bin/env python3
"""cola_aplicaciones.py — Cola de aplicaciones a vacantes (Wellfound).

Estados: pendiente → evaluando → cv_listo | descartado | saltado → enviado | error
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import COLA_APLICACIONES_PATH, APLICACION_MAX_DIA

ESTADOS = ("pendiente", "evaluando", "cv_listo", "aplicado", "descartado", "saltado", "error")

RE_WF_SECCION = re.compile(r"^##\s+Wellfound", re.I | re.M)
RE_SECCION_HEADER = re.compile(r"^##\s+", re.I | re.M)
RE_NUMERO = re.compile(r"^###\s+\d+\.\s+(.*)", re.I | re.M)
RE_EMPRESA = re.compile(r"\*\*Empresa:\*\*\s*(.+?)(?:\n|$)", re.I | re.M)
RE_UBICACION = re.compile(r"\*\*Ubicación:\*\*\s*(.+?)(?:\|\s*\*\*Modalidad|$)", re.I | re.M)
RE_SENIORITY = re.compile(r"\*\*Seniority:\*\*\s*(.+?)(?:\n|$)", re.I | re.M)
RE_URL = re.compile(r"\]\((https://wellfound\.com/[^)]+)\)")

RE_RELEVANTE = re.compile(r"\b(flutter|dart|mobile|android|ios)\b", re.I)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _short_hash(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]


class Cola:
    def __init__(self, path=COLA_APLICACIONES_PATH, max_dia=APLICACION_MAX_DIA):
        self.path = path
        self.max_dia = max_dia
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("aplicaciones"), list):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return {"aplicaciones": []}

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, aid):
        for a in self.data["aplicaciones"]:
            if a.get("id") == aid:
                return a
        return None

    def pendientes(self):
        return [dict(a) for a in self.data["aplicaciones"] if a.get("estado") in ("pendiente", "evaluando")]

    def listar(self, estado=None):
        return [dict(a) for a in self.data["aplicaciones"] if (not estado or a.get("estado") == estado)]

    def aplicados_hoy(self):
        t = today()
        return [a for a in self.data["aplicaciones"] if a.get("estado") == "aplicado" and (a.get("aplicado_en") or "")[:10] == t]

    def cupo_restante(self):
        return max(0, self.max_dia - len(self.aplicados_hoy()))

    def add(self, url, titulo, empresa, ubicacion="", seniority="", fuente="Wellfound"):
        url = (url or "").strip()
        if not url:
            raise ValueError("url vacía")
        for a in self.data["aplicaciones"]:
            if a.get("url") == url:
                return a, False
        aid = f"a-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.data['aplicaciones']) + 1}"
        entry = {
            "id": aid,
            "url": url,
            "titulo": titulo or "",
            "empresa": empresa or "",
            "ubicacion": ubicacion or "",
            "seniority": seniority or "",
            "fuente": fuente,
            "tipo": "mobile" if RE_RELEVANTE.search(titulo or "") else "otro",
            "estado": "pendiente",
            "motivo": "",
            "cv_md": "",
            "cv_pdf": "",
            "carta_md": "",
            "creado": now_iso(),
            "evaluado_en": None,
            "cv_listo_en": None,
            "aplicado_en": None,
            "error": None,
        }
        self.data["aplicaciones"].append(entry)
        self.save()
        return entry, True

    def add_many(self, items, solo_relevantes=False, dedup_urls=None):
        dedup_urls = set(dedup_urls or [a.get("url") for a in self.data["aplicaciones"]])
        n = 0
        for it in items:
            url = it.get("url")
            if not url or url in dedup_urls:
                continue
            titulo = it.get("titulo", "")
            if solo_relevantes and not RE_RELEVANTE.search(titulo):
                continue
            self.add(url, titulo, it.get("empresa", ""), ubicacion=it.get("ubicacion", ""), seniority=it.get("seniority", ""), fuente=it.get("fuente", "Wellfound"))
            dedup_urls.add(url)
            n += 1
        return n

    def marcar(self, aid, estado, motivo="", cv_md=None, cv_pdf=None, carta_md=None):
        if estado not in ESTADOS:
            raise ValueError(f"estado inválido: {estado!r}")
        for a in self.data["aplicaciones"]:
            if a.get("id") == aid:
                a["estado"] = estado
                if motivo:
                    a["motivo"] = motivo
                if estado == "aplicado":
                    a["aplicado_en"] = now_iso()
                    a["error"] = None
                elif estado == "error":
                    a["error"] = motivo or "error desconocido"
                elif estado == "descartado":
                    a["evaluado_en"] = a["evaluado_en"] or now_iso()
                elif estado == "cv_listo":
                    a["cv_listo_en"] = now_iso()
                if cv_md:
                    a["cv_md"] = cv_md
                if cv_pdf:
                    a["cv_pdf"] = cv_pdf
                if carta_md:
                    a["carta_md"] = carta_md
                self.save()
                return a
        return None


def _print_table(items):
    if not items:
        print("(ninguno)")
        return
    print(f"{'ID':<28} {'TIPO':<8} {'ESTADO':<10} {'EMPRESA':<22} {'TITULO':<48}")
    for a in items:
        print(f"{a['id']:<28} {a.get('tipo','otro'):<8} {a.get('estado','-'):<10} {str(a.get('empresa','-'))[:22]:<22} {str(a.get('titulo','-'))[:48]:<48}")


def poblar_archivo(path, fuente="Wellfound", solo_relevantes=False):
    try:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()
    except OSError as exc:
        raise ValueError(f"no se pudo leer: {exc}") from exc
    items = []
    if fuente.lower() == "wellfound":
        m = RE_WF_SECCION.search(txt)
        if not m:
            raise ValueError("no se encontró la sección '## Wellfound'")
        start = m.start()
        mnext = RE_SECCION_HEADER.search(txt, m.end() + 1)
        end = mnext.start() if mnext else len(txt)
        block = txt[start:end]
        for mnum in RE_NUMERO.finditer(block):
            titulo = mnum.group(1).strip()
            chunk = block[mnum.end():]
            mco = RE_EMPRESA.search(chunk)
            empresa = mco.group(1).strip() if mco else "No especificada"
            mub = RE_UBICACION.search(chunk)
            ubicacion = mub.group(1).strip() if mub else ""
            msen = RE_SENIORITY.search(chunk)
            seniority = msen.group(1).strip() if msen else ""
            murl = RE_URL.search(chunk)
            url = murl.group(1).strip() if murl else ""
            if url:
                items.append({"titulo": titulo, "empresa": empresa, "ubicacion": ubicacion, "seniority": seniority, "url": url, "fuente": "Wellfound"})
    return items


def main(argv=None):
    p = argparse.ArgumentParser(prog="cola_aplicaciones.py", description="Cola de aplicaciones a vacantes")
    sub = p.add_subparsers(dest="cmd")

    pa = sub.add_parser("add", help="añade una vacante")
    pa.add_argument("--url", required=True)
    pa.add_argument("--titulo", required=True)
    pa.add_argument("--empresa", required=True)
    pa.add_argument("--ubicacion", default="")
    pa.add_argument("--seniority", default="")
    pa.add_argument("--fuente", default="Wellfound")

    pp = sub.add_parser("poblar", help="puebla la cola desde un .md")
    pp.add_argument("--archivo", required=True)
    pp.add_argument("--fuente", default="Wellfound")
    pp.add_argument("--solo-relevantes", action="store_true")

    sub.add_parser("pendientes", help="pendientes/evaluando")
    pl = sub.add_parser("listar", help="listar")
    pl.add_argument("--estado", default=None)
    sub.add_parser("stats", help="estadísticas")
    sub.add_parser("aplicados-hoy", help="cupo/hoy")

    pv = sub.add_parser("ver", help="ver detalle")
    pv.add_argument("id")

    pm = sub.add_parser("marcar", help="marcar estado")
    pm.add_argument("id")
    pm.add_argument("estado", choices=ESTADOS)
    pm.add_argument("--motivo", default="")
    pm.add_argument("--cv-md", default=None)
    pm.add_argument("--cv-pdf", default=None)
    pm.add_argument("--carta-md", default=None)

    args = p.parse_args(argv)
    c = Cola()

    if args.cmd == "add":
        e, nuevo = c.add(args.url, args.titulo, args.empresa, args.ubicacion, args.seniority, args.fuente)
        print(f"{'Añadido' if nuevo else 'Ya existía'}: {e['id']} {e['url']}")
        return 0
    if args.cmd == "poblar":
        items = poblar_archivo(args.archivo, args.fuente, solo_relevantes=args.solo_relevantes)
        n = c.add_many(items, solo_relevantes=args.solo_relevantes)
        print(f"Añadidos: {n} (total ahora: {len(c.data['aplicaciones'])})")
        return 0
    if args.cmd == "pendientes":
        pnd = c.pendientes()
        print(f"{len(pnd)} pendientes/evaluando (cupo hoy: {c.cupo_restante()}/{c.max_dia})")
        _print_table(pnd)
        return 0
    if args.cmd == "listar":
        xs = c.listar(args.estado)
        print(f"{len(xs)} items estado={args.estado or 'todos'}")
        _print_table(xs)
        return 0
    if args.cmd == "stats":
        def cnt(est): return len([a for a in c.data["aplicaciones"] if a.get("estado") == est])
        for e in ESTADOS:
            print(f"  {e:<12} {cnt(e)}")
        print(f"  aplicados hoy: {len(c.aplicados_hoy())}/{c.max_dia}")
        return 0
    if args.cmd == "aplicados-hoy":
        n = len(c.aplicados_hoy())
        print(f"aplicados hoy: {n}/{c.max_dia} — cupo restante: {c.cupo_restante()}")
        return 0
    if args.cmd == "ver":
        a = c.get(args.id)
        if not a:
            print(f"No existe {args.id}")
            return 1
        print(json.dumps(a, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "marcar":
        a = c.marcar(args.id, args.estado, args.motivo, args.cv_md, args.cv_pdf, args.carta_md)
        if not a:
            print(f"No existe {args.id}")
            return 1
        print(f"{args.id} → {args.estado}")
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
