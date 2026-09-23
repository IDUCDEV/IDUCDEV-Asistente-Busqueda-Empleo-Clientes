#!/usr/bin/env python3
"""enviar_email.py — Envío de emails transaccionales por SMTP (Gmail).

Sin dependencias externas: solo librería estándar de Python.
Credenciales en `.env` en la raíz del proyecto (NO commitear .env):

    EMAIL_USER=iducdev.inc@gmail.com
    EMAIL_APP_PASSWORD=<contraseña de app de Gmail>

Uso:
    # Enviar un envío de la cola (y marcarlo enviado/error automáticamente):
    python3 enviar_email.py --id e-YYYYMMDDHHMMSS-N

    # Envío directo (pruebas / sin cola):
    python3 enviar_email.py --to destino@ejemplo.com --subject "Asunto" \
        --body "Hola..." [--dry-run]

    # Solo validar credenciales:
    python3 enviar_email.py --check
"""

import argparse
import os
import smtplib
import sys
from email.message import EmailMessage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cola_envios import Cola
from config import EMAIL_APP_PASSWORD, EMAIL_USER

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(to, subject, body, user=None, password=None, dry_run=False):
    user = user or EMAIL_USER
    password = password or EMAIL_APP_PASSWORD
    if not user or not password:
        raise RuntimeError(
            "Faltan credenciales: defina EMAIL_USER y EMAIL_APP_PASSWORD en el .env de la raíz "
            "(contraseña de app de Gmail). Vea .env.example."
        )
    if dry_run:
        print(f"[dry-run] de={user} para={to} asunto={subject!r} ({len(body)} chars)")
        return True
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject or "(sin asunto)"
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(user, password)
        smtp.send_message(msg)
    return True


def main(argv=None):
    p = argparse.ArgumentParser(prog="enviar_email.py", description="Envío email por SMTP")
    p.add_argument("--id", help="id de envío en cola_envios.json (lo marca enviado/error)")
    p.add_argument("--to", help="destino (email)")
    p.add_argument("--subject", default="")
    p.add_argument("--body", default="")
    p.add_argument("--body-file", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--check", action="store_true", help="valida credenciales y sale")
    args = p.parse_args(argv)

    if args.check:
        if not EMAIL_USER or not EMAIL_APP_PASSWORD:
            print("FALTA: EMAIL_USER / EMAIL_APP_PASSWORD no definidos en .env")
            return 1
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(EMAIL_USER, EMAIL_APP_PASSWORD)
            print(f"OK: autenticación correcta como {EMAIL_USER}")
            return 0
        except Exception as exc:  # noqa: BLE001 — reportar cualquier fallo SMTP
            print(f"ERROR: {exc}")
            return 1

    if args.id:
        cola = Cola()
        entry = cola.get(args.id)
        if not entry:
            print(f"No existe el envío {args.id}")
            return 1
        if entry.get("estado") == "enviado":
            print(f"{args.id} ya estaba enviado.")
            return 0
        if entry["canal"] != "email":
            print(f"{args.id} es canal {entry['canal']}, no email.")
            return 1
        try:
            send_email(entry["destino"], entry.get("asunto", ""), entry.get("cuerpo", ""),
                       dry_run=args.dry_run)
        except Exception as exc:  # noqa: BLE001
            cola.marcar(args.id, "error", motivo=str(exc))
            print(f"ERROR enviando {args.id}: {exc}")
            return 1
        if not args.dry_run:
            cola.marcar(args.id, "enviado")
        print(f"{'[dry-run] ' if args.dry_run else ''}Enviado {args.id} → {entry['destino']}")
        return 0

    if not args.to:
        p.error("indique --id, --to o --check")
    body = args.body
    if args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as f:
            body = f.read()
    if not body:
        p.error("el cuerpo está vacío (--body / --body-file)")
    try:
        send_email(args.to, args.subject, body, dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1
    print(f"{'[dry-run] ' if args.dry_run else ''}Enviado a {args.to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
