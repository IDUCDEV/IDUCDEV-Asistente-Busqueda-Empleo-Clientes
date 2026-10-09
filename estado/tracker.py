#!/usr/bin/env python3
"""tracker.py — Base de datos central de deduplicación.

Registra TODO lo ya visto (vacantes, empresas, clientes, posts de LinkedIn y
mensajes de outreach) en estado/historial.json.

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
    h.set_state("vacantes", key, "applied")

Ciclo de vida del estado: nuevo → revisado → en_proceso → aplicado/enviado
→ respuesta/descartado. `h.vencidos(dias)` devuelve items con estado
(enviado/applied/contactado) cuya última actualización supera `dias`
(usado para generar follow-ups automáticos).

Uso standalone (CLI):
    python3 tracker.py stats                 # conteo por categoría
    python3 tracker.py estado                # tablero (pendientes + vencidos)
    python3 tracker.py vencidos [dias]       # seguimientos vencidos
    python3 tracker.py estados <cat>         # items con su estado
    python3 tracker.py buscar <cat> <texto>  # búsqueda en claves
    python3 tracker.py normalizar [--dry-run]  # canoniza y deduplica claves de vacantes
    python3 tracker.py purge                 # limpia categorías vacías
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

# TLDs compuestos de 2 letras (ej: .com.br, .co.ve, .com.mx, .net.ar)
_CC_TLDS = {
    "ac", "ad", "ae", "af", "ag", "al", "am", "ar", "as", "at", "au", "aw",
    "az", "ba", "bb", "bd", "be", "bf", "bg", "bh", "bi", "bj", "bm", "bn",
    "bo", "br", "bs", "bt", "bw", "by", "bz", "ca", "cc", "cd", "cf", "cg",
    "ch", "ci", "ck", "cl", "cm", "cn", "co", "cr", "cu", "cv", "cx", "cy",
    "cz", "de", "dj", "dk", "dm", "do", "dz", "ec", "ee", "eg", "er", "es",
    "et", "eu", "fi", "fj", "fk", "fm", "fo", "fr", "ga", "gb", "gd", "ge",
    "gf", "gg", "gh", "gi", "gl", "gm", "gn", "gp", "gq", "gr", "gs", "gt",
    "gu", "gw", "gy", "hk", "hm", "hn", "hr", "ht", "hu", "id", "ie", "il",
    "im", "in", "io", "iq", "ir", "is", "it", "je", "jm", "jo", "jp", "ke",
    "kg", "kh", "ki", "km", "kn", "kp", "kr", "kw", "ky", "kz", "la", "lb",
    "lc", "li", "lk", "lr", "ls", "lt", "lu", "lv", "ly", "ma", "mc", "md",
    "me", "mg", "mh", "mk", "ml", "mm", "mn", "mo", "mp", "mq", "mr", "ms",
    "mt", "mu", "mv", "mw", "mx", "my", "mz", "na", "nc", "ne", "nf", "ng",
    "ni", "nl", "no", "np", "nr", "nu", "nz", "om", "pa", "pe", "pf", "pg",
    "ph", "pk", "pl", "pm", "pn", "pr", "ps", "pt", "pw", "py", "qa", "re",
    "ro", "rs", "ru", "rw", "sa", "sb", "sc", "sd", "se", "sg", "sh", "si",
    "sk", "sl", "sm", "sn", "so", "sr", "ss", "st", "su", "sv", "sx", "sy",
    "sz", "tc", "td", "tf", "tg", "th", "tj", "tk", "tl", "tm", "tn", "to",
    "tr", "tt", "tv", "tw", "tz", "ua", "ug", "uk", "us", "uy", "uz", "va",
    "vc", "ve", "vg", "vi", "vn", "vu", "wf", "ws", "ye", "yt", "za", "zm", "zw",
}

from config import HISTORIAL_PATH, PROJECT_DIR

CATEGORIES = {
    "vacantes": "clave: empresa::titulo normalizados",
    "empresas": "clave: dominio o nombre normalizado",
    "clientes": "clave: dominio o nombre del negocio",
    "posts_linkedin": "clave: URL del post",
    "outreach": "clave: URL del perfil contactado",
    "vacantes_empresa": "clave: empresa::titulo normalizados (tableros ATS directos)",
}

# Categorías cuya clave SIEMPRE es `empresa::titulo`. Cualquier otra forma se
# canoniza al escribir (ver Historial.add) para que el dedup sea unificado.
VACANCY_CATEGORIES = ("vacantes", "vacantes_empresa")


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


# ── Canonización de claves de vacantes ─────────────────────────────────
# Antes convivían dos convenciones en las mismas categorías: la cruda
# ("Zeely::Tech Lead Flutter") y la normalizada ("zeely::tech lead flutter").
# El dedup comparaba strings, así que la misma vacante se guardaba dos veces y
# volvía a listarse como "nueva" en cada ronda. Ahora toda clave pasa por
# `_canon_vacancy_key` al escribir, y `normalize_vacancy_keys` limpia el
# historial ya contaminado.

_ESTADO_RANK = {
    "nuevo": 0, "revisado": 1, "en_cola": 2,
    "enviado": 3, "contactado": 3,
    "en_proceso": 4,
    "applied": 5, "aplicado": 5, "respuesta": 5,
    "descartado": 6,
}


def canon_vacancy_key(key, meta=None):
    """Lleva cualquier clave de vacante a la forma canónica `empresa::titulo`.

    Prefiere `meta` (empresa/titulo) porque es la fuente real; si no está, parte
    de la propia clave. Si no hay empresa reconocible devuelve "" para no crear
    una clave degenerada tipo "::titulo" que fusionaría vacantes distintas.
    """
    if meta:
        empresa = str(meta.get("empresa") or "").strip()
        titulo = str(meta.get("titulo") or "").strip()
        if empresa and titulo:
            return vacancy_key(empresa, titulo)
    key = str(key or "")
    if "::" in key:
        empresa, _, titulo = key.partition("::")
        empresa, titulo = empresa.strip(), titulo.strip()
        if empresa and titulo:
            return vacancy_key(empresa, titulo)
    return ""


def _best_state(states):
    """El estado más avanzado de los fusionados (descartado > aplicado > ... > nuevo)."""
    valid = [s for s in states if s]
    if not valid:
        return "nuevo"
    return max(valid, key=lambda s: _ESTADO_RANK.get(s, 0))


def normalize_vacancy_keys(historial, dry_run=False):
    """Canoniza y deduplica las categorías de vacantes de un historial en memoria.

    Al fusionar dos registros de la misma vacante se conserva el estado más
    avanzado, la `fecha_visto` más antigua (cuándo la viste por primera vez) y
    la `fecha_actualizado` más reciente. Devuelve {categoría: {antes, despues,
    fusionadas}}.
    """
    resumen = {}
    for cat in VACANCY_CATEGORIES:
        items = historial.get(cat)
        if not isinstance(items, list) or not items:
            continue
        fused = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            key = canon_vacancy_key(item.get("key"), item)
            if not key:
                continue
            prev = fused.get(key)
            if prev is None:
                merged = dict(item)
                merged["key"] = key
                fused[key] = merged
                continue
            prev["estado"] = _best_state([prev.get("estado"), item.get("estado")])
            vistos = [v for v in (prev.get("fecha_visto"), item.get("fecha_visto")) if v]
            if vistos:
                prev["fecha_visto"] = min(vistos)
            acts = [v for v in (prev.get("fecha_actualizado"), item.get("fecha_actualizado")) if v]
            if acts:
                prev["fecha_actualizado"] = max(acts)
            # Rellena metadata que el primer registro no tenía (p. ej. `tablero`).
            for campo, valor in item.items():
                if campo in ("key", "estado", "fecha_visto", "fecha_actualizado"):
                    continue
                if valor is not None and not prev.get(campo):
                    prev[campo] = valor
        limpio = sorted(fused.values(), key=lambda i: i.get("fecha_visto") or "")
        resumen[cat] = {
            "antes": len(items),
            "despues": len(limpio),
            "fusionadas": len(items) - len(limpio),
        }
        if not dry_run and limpio != items:
            historial[cat] = limpio
    return resumen


def domain_key(domain):
    """Extrae el dominio raíz (ej: www.sub.empresa.com -> empresa.com).
    Respeta TLDs compuestos de país (ej: app.empresa.com.br -> empresa.com.br)."""
    if not domain:
        return ""
    d = domain.lower().strip().replace("http://", "").replace("https://", "").rstrip("/")
    parts = [p for p in d.split(".") if p]
    if len(parts) >= 2:
        if len(parts[-1]) == 2 and parts[-1] in _CC_TLDS and len(parts) >= 3:
            return ".".join(parts[-3:])
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
        key = self._resolve_key(category, key)
        for item in self.data.get(category, []):
            if item.get("key") == key:
                return item
        return None

    def _resolve_key(self, category, key):
        """Canoniza la clave si la categoría es de vacantes (ver canon_vacancy_key)."""
        key = str(key or "")
        if category in VACANCY_CATEGORIES:
            canon = canon_vacancy_key(key)
            if canon:
                return canon
        return key

    def is_known(self, category, key):
        return self.get(category, key) is not None

    def add(self, category, key, meta=None):
        """Registra un item. Devuelve True si es NUEVO (se agregó), False si ya existía."""
        key = str(key).strip()
        if not key:
            return False
        if category in VACANCY_CATEGORIES:
            # Toda clave de vacante pasa por la forma canónica. Si no se puede
            # canonizar (sin empresa reconocible) se cae de vuelta a la clave tal
            # cual: es preferible una clave fea a perder la vacante.
            canon = canon_vacancy_key(key, meta)
            if canon:
                key = canon
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
        """Actualiza el estado de un item: nuevo|aplicado|descartado|contactado..."""
        key = self._resolve_key(category, key)
        for item in self.data.get(category, []):
            if item.get("key") == key:
                item["estado"] = state
                item["fecha_actualizado"] = now_iso()
                self.save()
                return True
        return False

    def by_state(self, category, states=None):
        """Devuelve items de una categoría filtrados por su `estado`."""
        items = self.data.get(category, [])
        if states is None:
            return [dict(i) for i in items]
        # Acepta un estado suelto ("nuevo") o varios (("nuevo", "en_proceso")).
        # Sin esto, set("nuevo") sería un set de letras y el filtro nunca
        # coincidiría: fallo silencioso.
        if isinstance(states, str):
            states = (states,)
        states = set(states)
        return [dict(i) for i in items if i.get("estado") in states]

    def pendientes(self, estados=("nuevo", "en_proceso")):
        """Resumen de items que requieren acción, agrupados por categoría."""
        return {cat: self.by_state(cat, estados) for cat in CATEGORIES}

    def vencidos(self, dias, estados=("enviado", "applied", "contactado")):
        """Items con estado dado cuya última actualización supera `dias` (para seguimiento)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=dias)
        out = []
        for cat in CATEGORIES:
            for i in self.data.get(cat, []):
                if i.get("estado") not in estados:
                    continue
                ts = i.get("fecha_actualizado") or i.get("fecha_visto") or ""
                try:
                    d = datetime.fromisoformat(ts)
                except Exception:
                    continue
                if d < cutoff:
                    out.append({**i, "categoria": cat})
        return out

    def stats(self):
        return {cat: len(self.data.get(cat, [])) for cat in CATEGORIES}


def main():
    h = Historial()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(f"Historial: {h.path}")
        for cat, n in h.stats().items():
            print(f"  {cat}: {n}")
    elif cmd == "estado":
        print(f"Historial: {h.path}\n")
        print("=== Tablero del asistente ===")
        for cat, n in h.stats().items():
            print(f"  {cat:<18} {n}")
        pen = h.pendientes()
        total_pen = sum(len(v) for v in pen.values())
        print(f"\nPendientes de acción (nuevo/en_proceso): {total_pen}")
        for cat, items in pen.items():
            if items:
                print(f"  {cat}: {len(items)}")
        vencidos = h.vencidos(3)
        print(f"\nSeguimientos vencidos (3+ días): {len(vencidos)}")
        for it in vencidos:
            print(f"  [{it['categoria']}] {it.get('key')} ({it.get('estado')})")
    elif cmd == "vencidos":
        dias = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        for it in h.vencidos(dias):
            print(f"[{it['categoria']}] {it.get('key')} ({it.get('estado')})")
    elif cmd == "estados":
        cat = sys.argv[2] if len(sys.argv) > 2 else "vacantes"
        for it in h.data.get(cat, []):
            print(f"  {it.get('estado', '-'):<12} {it.get('fecha_visto', '')[:10]} {it['key']}")
    elif cmd == "buscar":
        cat = sys.argv[2] if len(sys.argv) > 2 else "vacantes"
        sub = sys.argv[3] if len(sys.argv) > 3 else ""
        for it in h.data.get(cat, []):
            if sub in it["key"].lower():
                print(f"  {it.get('estado', '-'):<12} {it['key']}")
    elif cmd == "normalizar":
        dry = "--dry-run" in sys.argv
        resumen = normalize_vacancy_keys(h.data, dry_run=dry)
        if not resumen:
            print("No hay categorías de vacantes que normalizar.")
        for cat, r in resumen.items():
            etiqueta = "[dry-run] " if dry else ""
            print(f"{etiqueta}{cat}: {r['antes']} → {r['despues']} items "
                  f"({r['fusionadas']} duplicadas fusionadas)")
        if not dry:
            h.save()
    elif cmd == "purge":
        empty = [c for c, n in h.stats().items() if n == 0]
        for cat in list(h.data):
            if cat not in CATEGORIES:
                del h.data[cat]
        h.save()
        print(f"Categorías vacías: {empty or 'ninguna'}. Historial limpio.")
    else:
        print(f"Comando desconocido: {cmd}")
        print("Uso: stats | estado | vencidos [dias] | estados <cat> | buscar <cat> <substr>"
              " | normalizar [--dry-run] | purge")
        sys.exit(1)


if __name__ == "__main__":
    main()