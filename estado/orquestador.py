#!/usr/bin/env python3
"""orquestador.py — El "agente delegado": coordina rondas, estado y seguimientos.

Centraliza el cerebro del asistente:
  * historial.json  → qué ya se vio (dedup)
  * tareas.json     → qué hay que hacer (bandeja de entrada) y cuándo
  * rondas.json     → qué se hizo hoy (bitácora de rondas)
  * informes/*.md   → resumen diario consolidado

Comandos:

  python3 orquestador.py ronda [--empleos|--clientes]
        Ejecuta la ronda: lanza job_search.py y workana_search.py,
        registra las fases en rondas.json y regenera el informe del día.
        (Las fases de navegador —linkedin-hidden-jobs, prospectar-clientes,
        flutter-employers— las ejecuta la IA y se registran aparte.)

  python3 orquestador.py registrar <fase> <archivo> [--nuevas N] [--omitidas N] [--errores "a;b"] [--notas "..."]
        Registra una fase ejecutada manualmente (por la IA o el usuario).

  python3 orquestador.py estado
        Tablero: historial + tareas pendientes + seguimientos vencidos.

  python3 orquestador.py marcar <categoria> <key> <estado>
        Cambia el estado de un item en historial.json. Si el nuevo estado es
        aplicado, enviado o contactado, crea automáticamente la tarea de
        seguimiento (outreach D+3 / vacantes,workana D+7).

  python3 orquestador.py tareas
        Lista las tareas pendientes (bandeja de entrada).

  python3 orquestador.py tarea-done <id>
        Marca una tarea como hecha.

  python3 orquestador.py seguimientos
        Muestra seguiamientos vencidos y tareas próximas a vencer.

  python3 orquestador.py informe
        (Re)genera informes/{YYYY-MM-DD}-resumen.md a partir de rondas.json.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (ESTADO_DIR, OUTPUT_DIRS, PROJECT_DIR, RONDAS_PATH,
                    SEGUIMIENTO_DIAS, SKILL_SCRIPTS, TAREAS_PATH)
from tracker import Historial

VERSIONADO = "orquestador 1.0"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─────────────────────────────── Tareas ───────────────────────────────


def load_tareas():
    return load_json(TAREAS_PATH, {"tareas": []})


def tarea_nueva(tipo, categoria, key, titulo, url="", dias=None):
    data = load_tareas()
    tid = f"t-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(data['tareas']) + 1}"
    venc = datetime.now(timezone.utc) + timedelta(days=dias if dias else 3)
    tarea = {
        "id": tid,
        "tipo": tipo,
        "categoria": categoria,
        "key": key,
        "titulo": titulo,
        "url": url,
        "creado": now_iso(),
        "vencimiento": venc.isoformat(timespec="seconds"),
        "estado": "pendiente",
    }
    data["tareas"].append(tarea)
    save_json(TAREAS_PATH, data)
    return tarea


def _tarea_existe(tipo, key):
    return any(
        t.get("tipo") == tipo and t.get("key") == key and t.get("estado") == "pendiente"
        for t in load_tareas()["tareas"]
    )


def tareas_pendientes():
    return [t for t in load_tareas()["tareas"] if t.get("estado") == "pendiente"]


def tarea_done(tid):
    data = load_tareas()
    for t in data["tareas"]:
        if t["id"] == tid:
            t["estado"] = "hecho"
            t["fecha_hecho"] = now_iso()
            save_json(TAREAS_PATH, data)
            return True
    return False


def _parse_venc(ts):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


# ─────────────────────────────── Rondas ───────────────────────────────


def load_rondas():
    return load_json(RONDAS_PATH, {"rondas": []})


def _ronda_hoy(tipo="parcial"):
    """Devuelve (rondas, ronda_del_día) creándola si no existe (idempotente)."""
    rondas = load_rondas()
    r = next((x for x in rondas["rondas"] if x.get("fecha") == today()), None)
    if r is None:
        r = {"fecha": today(), "inicio": now_iso(), "tipo": tipo, "fases": []}
        rondas["rondas"].insert(0, r)
    if not r.get("fases"):
        r["tipo"] = tipo
    save_json(RONDAS_PATH, rondas)
    return rondas, r


def registrar_fase(fase, archivo, nuevas=0, omitidas=0, errores=None, notas="", tipo="parcial"):
    """Registra el resultado de una fase en la ronda del día (idempotente por fase)."""
    rondas, r = _ronda_hoy(tipo)
    if archivo and os.path.isabs(archivo) and archivo.startswith(PROJECT_DIR):
        archivo = os.path.relpath(archivo, PROJECT_DIR)
    r["fases"] = [f for f in r["fases"] if f.get("fase") != fase]
    r["fases"].append({
        "fase": fase,
        "archivo": archivo,
        "nuevas": int(nuevas or 0),
        "omitidas": int(omitidas or 0),
        "errores": errores or [],
        "ok": not errores,
        "notas": notas or "",
        "fin": now_iso(),
    })
    save_json(RONDAS_PATH, rondas)
    generar_informe()
    return r


# ─────────────────────────── Scripts (ronda) ───────────────────────────


def _parse_script_output(stdout):
    """Extrae las secciones ---JOBCOUNT---/---SKIPPED---/---SOURCES---/---ERRORS---."""
    res = {"path": None, "nuevas": 0, "omitidas": 0, "fuentes": {}, "errores": []}
    lines = stdout.splitlines()
    section = "head"
    for ln in lines:
        stripped = ln.strip()
        if stripped == "---JOBCOUNT---":
            section = "count"
        elif stripped == "---SKIPPED---":
            section = "skipped"
        elif stripped == "---SOURCES---":
            section = "sources"
        elif stripped == "---ERRORS---":
            section = "errors"
        elif stripped.startswith("---") and stripped.endswith("---"):
            section = "head"
        elif section == "head" and stripped:
            if res["path"] is None and not ln.startswith("#"):
                res["path"] = stripped
        elif section == "count" and stripped:
            try:
                res["nuevas"] = int(stripped)
            except ValueError:
                pass
        elif section == "skipped" and stripped:
            try:
                res["omitidas"] = int(stripped)
            except ValueError:
                pass
        elif section == "sources" and ":" in ln:
            k, _, v = ln.partition(":")
            res["fuentes"][k.strip()] = v.strip()
        elif section == "errors" and stripped:
            res["errores"].append(stripped)
    return res


def _run_script(nombre, script):
    if not os.path.exists(script):
        return None, f"{nombre}: no existe el script {script}"
    try:
        proc = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        return None, f"{nombre}: timeout (10 min)"
    if proc.returncode != 0:
        tail = proc.stderr[-1200:] if proc.stderr else "(sin stderr)"
        return None, f"{nombre}: exit {proc.returncode}\n{tail}"
    return _parse_script_output(proc.stdout), None


def cmd_ronda(args):
    tipo = "empleos" if args.empleos else ("clientes" if args.clientes else "ronda_completa")
    rundas, r = _ronda_hoy(tipo)
    resultados = []

    for nombre, script in SKILL_SCRIPTS.items():
        print(f"== {nombre} en ejecución...", flush=True)
        res, err = _run_script(nombre, script)
        if err:
            print(f"   {err}")
            resultados.append((nombre, None, [err]))
            continue
        print(f"   {res['path']} | nuevas={res['nuevas']} omitidas={res['omitidas']}")
        errores = res["errores"]
        for e in errores:
            print(f"   [error fuente] {e}")
        registrar_fase(nombre, res["path"], res["nuevas"], res["omitidas"], errores,
                       notas="; ".join(f"{k}: {v}" for k, v in res["fuentes"].items()),
                       tipo=tipo)
        resultados.append((nombre, res, []))

    print("\nronda registrada. Informe: " + generar_informe())
    return 0


# ─────────────────────────────── informe ───────────────────────────────


def generar_informe():
    """Genera informes/{YYYY-MM-DD}-resumen.md a partir de rondas.json."""
    rondas = load_rondas()
    h = Historial()
    fecha = today()

    ronda_hoy = next((x for x in rondas["rondas"] if x.get("fecha") == fecha), None)

    lines = []
    lines.append(f"# Resumen diario — {fecha}")
    lines.append("")
    lines.append(f"_Generado por {VERSIONADO}. Sin commitear: revisar antes de publicar._")
    lines.append("")
    lines.append("## Estado del historial")
    lines.append("")
    lines.append("| Categoría | Total | Pendientes (nuevo/en_proceso) |")
    lines.append("|---|---|---|")
    for cat, n in h.stats().items():
        pen = len(h.pendientes(("nuevo", "en_proceso")).get(cat, []))
        lines.append(f"| {cat} | {n} | {pen} |")
    lines.append("")

    if ronda_hoy:
        lines.append("## Fases ejecutadas hoy")
        lines.append("")
        lines.append("| Fase | Nuevas | Omitidas | Ok | Archivo |")
        lines.append("|---|---|---|---|---|")
        for f in ronda_hoy.get("fases", []):
            ok = "✅" if f.get("ok") else "❌"
            notas = f.get("notas", "")
            archivo = f.get("archivo", "-") or "-"
            line = f"| {f['fase']} | {f.get('nuevas', 0)} | {f.get('omitidas', 0)} | {ok} | `{archivo}` |"
            lines.append(line)
            if notas:
                lines.append(f"  _notas: {notas}_")
        lines.append("")
    else:
        lines.append("## Fases ejecutadas hoy")
        lines.append("_(aún no se registró ninguna fase hoy)_")
        lines.append("")

    pend = tareas_pendientes()
    lines.append("## Bandeja de entrada (tareas)")
    lines.append("")
    if pend:
        for t in pend:
            venc = t.get("vencimiento", "")[:10]
            lines.append(f"- [ ] `{t['id']}` **{t['titulo']}** ({t['categoria']}, vence {venc})")
        lines.append("")
    else:
        lines.append("_Sin tareas pendientes._")
        lines.append("")

    lines.append("## Seguimientos vencidos (3+ días)")
    lines.append("")
    vencidos = h.vencidos(3)
    if vencidos:
        for it in vencidos:
            lines.append(f"- [{it['categoria']}] {it.get('key')} ({it.get('estado')})")
        lines.append("")
    else:
        lines.append("_Ninguno._")

    texto = "\n".join(lines)
    out = os.path.join(OUTPUT_DIRS["informes"], f"{fecha}-resumen.md")
    os.makedirs(OUTPUT_DIRS["informes"], exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(texto)
    return out


# ─────────────────────────────── seguimientos ───────────────────────────────


def crear_seguimientos(auto=True):
    """Genera tareas de seguimiento a partir del historial y de las rondas."""
    h = Historial()
    creados = 0
    # Outreach: enviados hace >= 3 días sin respuesta registrada
    for it in h.by_state("outreach", ("enviado", "contactado")):
        ts = it.get("fecha_actualizado") or it.get("fecha_visto") or ""
        try:
            d = datetime.fromisoformat(ts)
        except Exception:
            d = datetime.now(timezone.utc)
        dias = (datetime.now(timezone.utc) - d).days
        if dias >= SEGUIMIENTO_DIAS.get("outreach", 3) and not _tarea_existe("seguimiento_outreach", it["key"]):
            tarea_nueva("seguimiento_outreach", "outreach", it["key"],
                        f"Revisar respuesta de outreach: {it['key']}",
                        url=it.get("url", ""), dias=1)
            creados += 1
    # Vacantes/workana: aplicados hace >= 7 días sin respuesta
    for cat in ("vacantes", "proyectos_workana"):
        for it in h.by_state(cat, ("applied", "enviado")):
            ts = it.get("fecha_actualizado") or it.get("fecha_visto") or ""
            try:
                d = datetime.fromisoformat(ts)
            except Exception:
                d = datetime.now(timezone.utc)
            dias = (datetime.now(timezone.utc) - d).days
            if dias >= SEGUIMIENTO_DIAS.get(cat, 7) and not _tarea_existe("seguimiento_aplicacion", it["key"]):
                tarea_nueva("seguimiento_aplicacion", cat, it["key"],
                            f"Seguimiento de aplicación: {it['key']}",
                            url=it.get("url", ""), dias=1)
                creados += 1
    return creados


def cmd_seguimientos(args):
    creados = crear_seguimientos()
    if creados:
        print(f"Creadas {creados} tareas de seguimiento automáticas.\n")
    h = Historial()
    vencidos = h.vencidos(args.dias)
    print(f"=== Seguimientos vencidos ({args.dias} días) ===")
    if not vencidos:
        print("  (ninguno)")
    for it in vencidos:
        print(f"  [{it['categoria']}] {it.get('key')} ({it.get('estado')})")
    pend = tareas_pendientes()
    print(f"\n=== Bandeja: {len(pend)} pendiente(s) ===")
    for t in pend:
        venc = t.get("vencimiento", "")[:10]
        print(f"  {t['id']}  {t['titulo']}  [vence {venc}]")


# ─────────────────────────────── marcar ───────────────────────────────


def cmd_marcar(args):
    h = Historial()
    ok = h.set_state(args.categoria, args.key, args.estado)
    if not ok:
        print(f"No existe {args.categoria}/{args.key} en historial.json")
        return 1
    print(f"Marcado {args.categoria}/{args.key} → {args.estado}")
    # crear tarea de seguimiento si corresponde
    if args.estado in ("enviado", "applied", "contactado"):
        key = args.key
        tipo = {
            "enviado": "seguimiento_outreach",
            "contactado": "seguimiento_outreach",
            "applied": "seguimiento_aplicacion",
        }[args.estado]
        if not _tarea_existe(tipo, key):
            dias = SEGUIMIENTO_DIAS.get(args.categoria, SEGUIMIENTO_DIAS.get("outreach", 3))
            tarea_nueva(tipo, args.categoria, key,
                        f"Seguimiento: {key}", dias=dias)
            print(f"Tarea de seguimiento creada (en {dias} días).")
    # regenerar informe para reflejar el cambio
    generar_informe()
    return 0


def cmd_estado(args):
    h = Historial()
    print(f"{VERSIONADO} — {PROJECT_DIR}\n")
    print("=== Historial ===")
    for cat, n in h.stats().items():
        print(f"  {cat:<18} {n}")
    pend = tareas_pendientes()
    print(f"\n=== Bandeja: {len(pend)} pendiente(s) ===")
    for t in pend:
        print(f"  {t['id']}  {t['titulo']}  [vence {t.get('vencimiento','')[:10]}]")
    vencidos = h.vencidos(args.dias)
    print(f"\n=== Seguimientos vencidos ({args.dias} días): {len(vencidos)} ===")
    for it in vencidos[:15]:
        print(f"  [{it['categoria']}] {it.get('key')} ({it.get('estado')})")


def cmd_tareas(args):
    pend = tareas_pendientes()
    if not pend:
        print("Bandeja vacía: sin tareas pendientes.")
        return 0
    print(f"{len(pend)} tarea(s) pendiente(s):\n")
    for t in pend:
        venc = t.get("vencimiento", "")[:10]
        print(f"  {t['id']}  [{t['tipo']}] {t['titulo']}")
        print(f"         {t['categoria']} · vence {venc} · {t.get('url','-')}")
    return 0


def cmd_tarea_done(args):
    if tarea_done(args.id):
        print(f"Tarea {args.id} marcada como hecha.")
        generar_informe()
        return 0
    print(f"No existe la tarea {args.id}")
    return 1


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="orquestador.py", description=VERSIONADO)
    sub = p.add_subparsers(dest="cmd")

    p_ronda = sub.add_parser("ronda", help="ejecuta la ronda (scripts CLI)")
    p_ronda.add_argument("--empleos", action="store_true", help="solo búsquedas de empleo")
    p_ronda.add_argument("--clientes", action="store_true", help="solo prospección de clientes")
    p_ronda.set_defaults(func=cmd_ronda)

    p_reg = sub.add_parser("registrar", help="registra una fase ejecutada manualmente")
    p_reg.add_argument("fase")
    p_reg.add_argument("archivo", nargs="?", default="")
    p_reg.add_argument("--nuevas", type=int, default=0)
    p_reg.add_argument("--omitidas", type=int, default=0)
    p_reg.add_argument("--errores", default="")
    p_reg.add_argument("--notas", default="")
    p_reg.add_argument("--tipo", default="parcial", choices=["parcial", "empleos", "clientes", "ronda_completa"])
    p_reg.set_defaults(func=lambda a: print_msg(a))

    def print_msg(a):
        registrar_fase(
            a.fase, a.archivo, a.nuevas, a.omitidas,
            [e.strip() for e in a.errores.split(";")] if a.errores else [],
            a.notas, tipo=a.tipo)
        print(f"Fase {a.fase} registrada.")

    for name in ("estado", "seguimientos"):
        p_s = sub.add_parser(name)
        p_s.add_argument("--dias", type=int, default=3)
        p_s.set_defaults(func=cmd_seguimientos if name == "seguimientos" else cmd_estado)

    p_m = sub.add_parser("marcar", help="cambia estado de un item del historial")
    p_m.add_argument("categoria")
    p_m.add_argument("key")
    p_m.add_argument("estado")
    p_m.set_defaults(func=cmd_marcar)

    sub.add_parser("tareas", help="lista tareas pendientes").set_defaults(func=cmd_tareas)
    p_td = sub.add_parser("tarea-done", help="marca tarea como hecha")
    p_td.add_argument("id")
    p_td.set_defaults(func=cmd_tarea_done)
    sub.add_parser("informe", help="(re)genera el informe del día").set_defaults(func=lambda a: print(generar_informe()))

    args = p.parse_args(argv)
    if not hasattr(args, "func"):
        p.print_help()
        print("\nEjemplos:")
        print("  python3 orquestador.py ronda --empleos")
        print("  python3 orquestador.py registrar linkedin-hidden-jobs vacantes-ocultas/2026-09-20.md --nuevas 4")
        print("  python3 orquestador.py marcar vacantes <key> applied")
        print("  python3 orquestador.py seguimientos")
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())