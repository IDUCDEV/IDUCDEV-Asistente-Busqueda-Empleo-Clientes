#!/usr/bin/env python3
"""tracker.py — Base de datos central de deduplicación.

Registra TODO lo ya visto (vacantes, empresas, clientes, proyectos de
Workana, posts de LinkedIn y mensajes de outreach) en estado/historial.json.

Su objetivo es que el asistente NUNCA vuelva a mostrarte:
  - una vacante ya listada
  - una empresa/cliente ya descubierto
  - un post de LinkedIn ya procesado
  - un mensaje de outreach ya generado

Uso desde otros scripts:
    from tracker import Historial
    h = Historial()
    h.add("vacantes", key, meta={"empresa": ..., "titulo": ...})
    h.is_known("vacantes", key)

Uso standalone (CLI):
    python3 tracker.py purge                # limpia categorías vacías
    python3 tracker.py stats                # cuenta items por categoría
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORIAL_PATH = os.path.join(PROJECT_DIR, "estado", "historial.json")

CATEGORIES = {
    "vacantes": "clave: empresa::titulo normalizados",
    "empresas": "clave: dominio o nombre normalizado",
    "clientes": "clave: dominio o nombre del negocio",
    "proyectos_workana": "clave: slug del proyecto",
    "posts_linkedin": "clave: URL del post",
    "outreach": "clave: URL del perfil contactado",
}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_company(c):
    """Normaliza un nombre de empresa para usarlo como parte de clave."""
    c = (c or "").lower().strip()
    c = re.sub(r"[^\w\s]", "", c)
    c = re.sub(r"\s+", " ", c)
    for suffix in [", inc", ", llc", ", s.a", ", s.a.s", ", s.a.c", ", c.a",
                   " inc", " llc", " s.a", " corp", " ltd", " s de rl",
                   " s.a. de c.v.", ", s.a. de c.v.", " sa de cv", ", sa de cv"]:
        if c.endswith(suffix):
            c = c[:-len(suffix)].strip()
    return c


def normalize_title(t):
    t = (t or "").lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def vacancy_key(company, title):
    return normalize_company(company) + "::" + normalize_title(title)


def domain_key(domain):
    """Extrae el dominio raíz (ej: www.sub.empresa.com -> empresa.com)."""
    if not domain:
        return ""
    d = domain.lower().strip().replace("http://", "").replace("https://", "").rstrip("/")
    parts = [p for p in d.split(".") if p]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return d


def is_known(historial, category, key):
    return any(item.get("key") == key for item in historial.get(category, []))


class Historial:
    """Carga, consulta y persiste el historial central de dedup."""

    def __init__(self, path=HISTORIAL_PATH):
        self.path = path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return {cat: [] for cat in CATEGORIES}

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def keys(self, category):
        return {item.get("key") for item in self.data.get(category, [])}

    def all(self, category, **filters):
        items = [dict(item) for item in self.data.get(category, [])]
        for k, v in filters.items():
            items = [i for i in items if i.get(k) == v]
        return items

    def get(self, category, key):
        for item in self.data.get(category, []):
            if item.get("key") == key:
                return item
        return None

    def is_known(self, category, key):
        return self.get(category, key) is not None

    def add(self, category, key, meta=None):
        """Registra un item. Devuelve True si es NUEVO (se agregó), False si ya existía."""
        key = str(key).strip()
        if not key:
            return False
        self.data.setdefault(category, [])
        for item in self.data[category]:
            if item.get("key") == key:
                if meta:
                    for k, v in meta.items():
                        if v is not None and k != "key":
                            item[k] = v
                return False
        entry = {"key": key, "fecha_visto": now_iso(), "estado": "nuevo"}
        if meta:
            for k, v in meta.items():
                if v is not None and k != "key":
                    entry[k] = v
        self.data[category].append(entry)
        self.save()
        return True

    def add_many(self, category, items):
        """Registra varios items. Devuelve la lista de los NUEVOS."""
        result = []
        for key, meta in items:
            if self.add(category, key, meta):
                result.append(meta or {"key": key})
        return result

    def set_state(self, category, key, state):
        """Actualiza el estado de un item: nuevo|aplicado|descartado|contactado."""
        for item in self.data.get(category, []):
            if item.get("key") == key:
                item["estado"] = state
                item["fecha_actualizado"] = now_iso()
                self.save()
                return True
        return False

    def stats(self):
        return {cat: len(self.data.get(cat, [])) for cat in CATEGORIES}


def main():
    h = Historial()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(f"Historial: {h.path}")
        for cat, n in h.stats().items():
            print(f"  {cat}: {n}")
    elif cmd == "purge":
        empty = [c for c, n in h.stats().items() if n == 0]
        for cat in list(h.data):
            if cat not in CATEGORIES:
                del h.data[cat]
        h.save()
        print(f"Categorías vacías: {empty or 'ninguna'}. Historial limpio.")
    else:
        print(f"Comando desconocido: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()