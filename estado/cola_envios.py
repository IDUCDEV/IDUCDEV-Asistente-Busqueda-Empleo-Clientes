#!/usr/bin/env python3
"""cola_envios.py — Cola de envíos de mensajes a clientes.

Puente entre `contactar-clientes` (genera el mensaje) y `enviar-clientes`
(lo envía por WhatsApp/email/LinkedIn). El `contactado` del historial (y su
seguimiento D+3) SOLO se marca tras un envío efectivo.

Estados de un envío:
    pendiente → enviado | error

Uso CLI:
    python3 cola_envios.py add --key <clave> --nombre <n> --canal whatsapp|email|linkedin \
        --destino <tel|email|url> --mensaje-path <ruta.md> [--asunto "..."] \
        [--cuerpo "..."] [--cuerpo-file <ruta>]
    python3 cola_envios.py pendientes
    python3 cola_envios.py enviados-hoy
    python3 cola_envios.py marcar <id> enviado|error [--motivo "..."]

Uso desde otros scripts:
    from cola_envios import Cola
    c = Cola()
    c.add(...)
    c.pendientes()
    c.enviados_hoy()
    c.marcar(id, "enviado")
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import COLA_ENVIOS_PATH, ENVIO_MAX_DIA

CANALES = ("whatsapp", "email", "linkedin")
ESTADOS = ("pendiente", "enviado", "error")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _extract_cuerpo_from_md(path):
    """Extrae la sección '## Mensaje' de un .md generado por contactar-clientes."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return ""
    out, grab = [], False
    for ln in lines:
        if not grab:
            if ln.strip().startswith("## Mensaje"):
                grab = True
            continue
        if ln.strip() == "---" or ln.strip().startswith("## "):
            break
        out.append(ln)
    return "\n".join(out).strip()


class Cola:
    """Cola persistente de envíos (estado/cola_envios.json)."""

    def __init__(self, path=COLA_ENVIOS_PATH, max_dia=ENVIO_MAX_DIA):
        self.path = path
        self.max_dia = max_dia
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("envios"), list):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return {"envios": []}

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, eid):
        for e in self.data["envios"]:
            if e.get("id") == eid:
                return e
        return None

    def pendientes(self):
        return [dict(e) for e in self.data["envios"] if e.get("estado") == "pendiente"]

    def enviados_hoy(self):
        t = today()
        return [
            e for e in self.data["envios"]
            if e.get("estado") == "enviado" and (e.get("enviado_en") or "")[:10] == t
        ]

    def cupo_restante(self):
        return max(0, self.max_dia - len(self.enviados_hoy()))

    def add(self, key, nombre, canal, destino, mensaje_path,
            asunto="", cuerpo=None, cuerpo_file=None):
        """Encola un envío. Dedup: mismo lead_key en pendiente → devuelve el existente."""
        canal = (canal or "").lower().strip()
        if canal not in CANALES:
            raise ValueError(f"canal inválido: {canal!r} (use: {', '.join(CANALES)})")
        key = str(key or "").strip()
        if not key:
            raise ValueError("key vacía")
        for e in self.data["envios"]:
            if e.get("lead_key") == key and e.get("estado") == "pendiente":
                return e, False
        if cuerpo is None and cuerpo_file:
            try:
                with open(cuerpo_file, "r", encoding="utf-8") as f:
                    cuerpo = f.read().strip()
            except OSError as exc:
                raise ValueError(f"no se pudo leer cuerpo_file: {exc}") from exc
        if cuerpo is None and mensaje_path:
            cuerpo = _extract_cuerpo_from_md(mensaje_path)
        if not cuerpo:
            raise ValueError("cuerpo vacío: pase --cuerpo, --cuerpo-file o un .md con sección '## Mensaje'")
        eid = f"e-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.data['envios']) + 1}"
        entry = {
            "id": eid,
            "lead_key": key,
            "nombre": nombre or key,
            "canal": canal,
            "destino": (destino or "").strip(),
            "asunto": asunto or "",
            "cuerpo": cuerpo,
            "mensaje_path": mensaje_path or "",
            "estado": "pendiente",
            "creado": now_iso(),
            "enviado_en": None,
            "error": None,
        }
        self.data["envios"].append(entry)
        self.save()
        return entry, True

    def marcar(self, eid, estado, motivo=""):
        if estado not in ESTADOS:
            raise ValueError(f"estado inválido: {estado!r} (use: {', '.join(ESTADOS)})")
        for e in self.data["envios"]:
            if e.get("id") == eid:
                e["estado"] = estado
                if estado == "enviado":
                    e["enviado_en"] = now_iso()
                    e["error"] = None
                elif estado == "error":
                    e["error"] = motivo or "error desconocido"
                self.save()
                return e
        return None

    def update(self, eid, asunto=None, cuerpo=None, destino=None, nombre=None):
        """Edita los campos de un envío pendiente antes de enviarlo."""
        for e in self.data["envios"]:
            if e.get("id") == eid:
                if e["estado"] != "pendiente":
                    raise ValueError(f"el envío {eid} no está pendiente (estado: {e['estado']})")
                if asunto is not None:
                    e["asunto"] = asunto
                if cuerpo is not None:
                    e["cuerpo"] = cuerpo
                if destino is not None:
                    e["destino"] = (destino or "").strip()
                if nombre is not None:
                    e["nombre"] = nombre or e.get("nombre", "")
                self.save()
                return e
        return None


def _print_table(envios):
    if not envios:
        print("(ninguno)")
        return
    print(f"{'ID':<28} {'CANAL':<10} {'NOMBRE':<28} DESTINO")
    for e in envios:
        print(f"{e['id']:<28} {e['canal']:<10} {e['nombre'][:28]:<28} {e.get('destino', '')}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="cola_envios.py", description="Cola de envíos a clientes")
    sub = p.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add", help="encola un envío")
    p_add.add_argument("--key", required=True)
    p_add.add_argument("--nombre", required=True)
    p_add.add_argument("--canal", required=True, choices=CANALES)
    p_add.add_argument("--destino", required=True, help="teléfono, email o URL de LinkedIn")
    p_add.add_argument("--mensaje-path", default="", help="ruta del .md generado")
    p_add.add_argument("--asunto", default="", help="asunto (solo email)")
    p_add.add_argument("--cuerpo", default=None)
    p_add.add_argument("--cuerpo-file", default=None)

    sub.add_parser("pendientes", help="lista envíos pendientes")
    p_hoy = sub.add_parser("enviados-hoy", help="cuenta envíos de hoy / cupo restante")
    p_m = sub.add_parser("marcar", help="marca un envío como enviado o error")
    p_m.add_argument("id")
    p_m.add_argument("estado", choices=("enviado", "error"))
    p_m.add_argument("--motivo", default="")

    p_ver = sub.add_parser("ver", help="muestra el mensaje completo de un envío pendiente")
    p_ver.add_argument("id")

    p_ed = sub.add_parser("editar", help="modifica un envío pendiente antes de enviarlo")
    p_ed.add_argument("id")
    p_ed.add_argument("--asunto", default=None, help="nuevo asunto (solo email)")
    p_ed.add_argument("--cuerpo", default=None, help="nuevo cuerpo del mensaje")
    p_ed.add_argument("--cuerpo-file", default=None, help="leer el nuevo cuerpo desde un .md")
    p_ed.add_argument("--destino", default=None)
    p_ed.add_argument("--nombre", default=None)

    args = p.parse_args(argv)
    c = Cola()

    if args.cmd == "add":
        entry, nuevo = c.add(
            args.key, args.nombre, args.canal, args.destino,
            args.mensaje_path, args.asunto, args.cuerpo, args.cuerpo_file,
        )
        print(f"{'Encolado' if nuevo else 'Ya estaba pendiente'}: {entry['id']} ({entry['nombre']})")
        return 0
    if args.cmd == "pendientes":
        pend = c.pendientes()
        print(f"{len(pend)} pendiente(s) de {c.max_dia}/día — cupo restante: {c.cupo_restante()}")
        _print_table(pend)
        return 0
    if args.cmd == "enviados-hoy":
        n = len(c.enviados_hoy())
        print(f"{n}/{c.max_dia} — cupo restante: {c.cupo_restante()}")
        return 0
    if args.cmd == "marcar":
        e = c.marcar(args.id, args.estado, args.motivo)
        if not e:
            print(f"No existe el envío {args.id}")
            return 1
        print(f"Envío {args.id} → {args.estado}" + (f" ({args.motivo})" if args.estado == "error" else ""))
        return 0
    if args.cmd == "ver":
        e = c.get(args.id)
        if not e:
            print(f"No existe el envío {args.id}")
            return 1
        print(f"== {e['id']} | {e['nombre']} | {e['canal']} → {e['destino']} ==")
        if e.get("asunto"):
            print(f"Asunto: {e['asunto']}")
        print("--- Mensaje ---")
        print(e.get("cuerpo", ""))
        return 0
    if args.cmd == "editar":
        cuerpo = None
        if args.cuerpo_file:
            cuerpo = _extract_cuerpo_from_md(args.cuerpo_file)
            if not cuerpo:
                print(f"Error: no se pudo extraer '## Mensaje' de {args.cuerpo_file}")
                return 1
        elif args.cuerpo is not None:
            cuerpo = args.cuerpo
        try:
            e = c.update(args.id, args.asunto, cuerpo, args.destino, args.nombre)
        except ValueError as exc:
            print(f"Error: {exc}")
            return 1
        if not e:
            print(f"No existe el envío {args.id}")
            return 1
        print(f"Editado: {e['id']} ({e['nombre']})")
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
