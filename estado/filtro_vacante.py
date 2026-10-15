#!/usr/bin/env python3
"""filtro_vacante.py — Pre-filtro de vacantes ANTES de gastar un CV.

Nace de 4 descartes consecutivos (Hansa, Walmart, QiBit, Mars) donde el
buscador trajo la vacante porque "Flutter" aparecia en el texto, pero no era
el centro del rol. Este script decide PASS/FAIL con reglas explicitas y
razones, para que cv-apply no tenga que gastar un analisis completo en un
descarte obvio.

Severidades:
  reject -> descarta automaticamente (marcarla `descartado` en el historial)
  warn   -> NO descarta; avisa de un gap conocido de tu perfil

Solo stdlib. No red: el texto se pasa por --archivo / --stdin / --texto.

Uso:
    python3 estado/filtro_vacante.py --titulo "Senior Android Developer" \\
        --empresa QiBit --archivo desc.txt
    curl -s <url> | python3 estado/filtro_vacante.py --titulo "..." --stdin
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import HISTORIAL_PATH  # noqa: E402

# --- Perfil de referencia (de recursos/cv/base-isaac-urdaneta.md) ---------
# Se hardcodean SOLO para puntuar la vacante, nunca para generar CV.
ANIOS_SW = 3          # años totales de software
ANIOS_FLUTTER = 2     # años con Flutter
NIVEL_ESPERADO = "mid-senior"

# --- F1: Flutter debe existir en el cuerpo -------------------------------
RE_FLUTTER = re.compile(r"\bflutter\b|\bdart\b", re.I)

# --- F2: Flutter solo dentro de "deseables" -------------------------------
RE_DESEJABLE = re.compile(
    r"(desej[áa]veis?|deseables?|nice to have|nice-to-have|plus|bonus|"
    r"diferencial|valorados?|s[ãa]oDiferenciais?|considera-se um plus)",
    re.I,
)
# Flutter cuenta como "de verdade" solo si aparece ANTES del primer marcador.
# OJO: LinkedIn/Indeed muestran el tipo de jornada como una ETIQUETA suelta en
# la tarjeta ("Presencial" / "Remoto" / "Hibrido"), no como frase. El regex solo
# sabia leer la forma espanola "modalidade de X hibrido", asi que una vacante
# marcada Presencial pasaba el filtro (caso ENGESOFTWARE Senior 2026-10-04:
# on-site en Brasilia, salario en BRL). Ahora se reconocen la etiqueta
# estructurada y la frase portuguesa. El guardia RE_REMOTO de F4 ya evita el
# falso positivo habitual ("presencial ou remoto" / "hibrido ou remoto").
RE_CONTRATO_LOCAL = re.compile(
    r"\b(CLT|EPS)\b|modalidade de (.+?)h[íi]brido|presencialidade|"
    r"\b(\d+)\s*[x/]\s*semana\s+presencial|trabalhar presencial|"
    r"trabalho\s+presencial|"
    # Modalidad declarada (ES "Modalidad híbrida/presencial", PT "Modalidade
    # presencial"). El patron antiguo solo conocia "modalidade/modelo/tipo" +
    # "presencial"; no leia la palabra espanola "modalidad" ni "híbrida". Caso
    # Start Companies 2026-10-09: "Modalidad híbrida en Tucuman" daba PASS.
    r"(?:modalidade|modalidad|modelo|tipo)\s*"
    r"(?:de\s+trabalho|de\s+trabajo|de\s+|do\s+)?\s*[:-]?\s*"
    r"(?:presencial|h[íi]brid[oa])\b|"
    # "Vaga/Contratacao Presencial em <ciudad>" (PremierSoft) y su variante ES.
    r"\b(?:vaga|contrata[çc][ãa]o|emprego)\s+(?:presencial|h[íi]brid[oa])\b|"
    r"\b(?:vacante|puesto|contrataci[óo]n)\s+(?:presencial|h[íi]brid[oa])\b|"
    r"^\s*presencial\s*$|"
    r"on-?site in person|no remoto|must be (located|based) in|"
    r"base(?:d)? em la ciudad|tienes base en|"
    # Requisito de residencia local ("Vivir en <Ciudad>", "Residir em <Ciudad>").
    # La (mayuscula) scoped exige un toponimo con mayuscula para no confundir
    # frases como "para vivir en remoto" con un requisito de ubicacion.
    r"(?:vivir|residir|radicar)(?:se)?\s+en\s+(?-i:[A-ZÁÉÍÓÚÑ])|"
    r"(?:vivir|residir|radicar)(?:se)?\s+en\b[^\n]{0,40}?alrededores",
    re.I | re.M,
)
RE_REMOTO = re.compile(
    r"\b(100%\s*remot[eo]|remote[- ]first|fully remote|remoto\b|"
    r"home[- ]office|work from home|anywhere)",
    re.I,
)

# --- F3: nivel inaccesible para 2-3 años de experiencia -------------------
# PT-BR: "coordenador"/"supervisor" son cargos jerárquicos igual que "lead".
# (NO se agrega "pleno": en PT significa nivel medio, pero tambien "pleno
# emprego" = jornada completa, que aparece en casi toda vacante BR.)
RE_NIVEL_ALTO = re.compile(
    r"\b(principal|staff|distinguished|lead|architect|head of|"
    r"director|manager|gerente)\b|"
    r"\b(coordenador|coordenadora|supervisor|supervisora)\b",
    re.I,
)
RE_NIVEL_BAJO = re.compile(r"\b(junior|trainee|becario|entry[- ]level)\b", re.I)

# --- F5: formación completa obligatoria (bloqueante D-08) ----------------
# OJO: los tres idiomas que llegan a la bandeja. Una vacante en portugues se
# escapaba entera porque F5 solo conocia ES/EN (caso ENGESOFTWARE 2026-10-04:
# "Ensino superior TI concluido" -> 0 hallazgos, PASS con 5 anos pedidos).
# PT-BR: "concluido/concluida" es explícito, asi que no hace falta interpretar
# "graduacao completa" (que en PT significa "carrera completa", no "terminada").
RE_FORMACION_OBLIG = re.compile(
    r"(forma(?:[çc][ãa]o|ci[óo]n)\s+superior\s+(completo|completa)|"
    r"licenciatura\s+(completa|em ci[êe]ncia)|"
    r"(four|4)[- ]year\s+degree|degree\s+(is\s+)?required|"
    r"graduaci[óo]n\s+(completa|obligatoria)|"
    r"must have a degree|bachelor'?s\s+degree\s+(required|mandatory)|"
    # --- PT-BR ---
    r"(?:ensino|forma[çc][ãa]o)\s+superior\s+[\w\s]{0,24}?conclu[íi]d[oa]|"
    r"superior\s+completo\s*\(\s*pleno\s*\)|"
    r"(?:bacharelado|licenciatura)\s+(?:em\s+[\w\s]{0,24}?)?conclu[íi]d[oa]|"
    r"ensino\s+superior\s+(?:completo|completa)|"
    # "Conclusao de nivel superior" = titulo TERMINADO, orden invertido respecto a
    # "ensino superior concluido". Sin esto la vacante Flutter/Dart de
    # ENGESOFTWARE (4474792135) daba PASS pidiendo nivel superior obligatorio.
    r"conclus[ãa]o\s+de\s+n[íi]vel\s+superior|"
    r"conclus[ãa]o\s+d[oa]s?\s+(?:curso|ensino|forma[çc][ãa]o)\s+superior)",
    re.I,
)

# --- F12: app movil YA publicada (requisito que no puedes cumplir) ---------
# El CV base tiene esto como regla de veracidad #5: "beta Android distribuida
# via GitHub Releases, 5 releases v1.0.0 -> v1.0.2, Google Play en camino.
# NUNCA afirmar 'publicado en Google Play' o 'en App Store'". Y el objetivo O-01
# confirma que Rifame sigue sin publicar. Una vacante que pone esto bajo
# "Requirements" es imposible de satisfacer sin mentir, asi que es bloqueante
# aunque el stack sea perfecto (caso Jobgether Senior Flutter 2026-10-04).
# Se ancla en la FENOLOGIA DE VERBO + SUSTANTIVO ("published apps"), no en la
# palabra "publish" suelta, para no chocar con "prepare releases to the store".
RE_APP_PUBLICADA = re.compile(
    r"(?:published|released|launched|shipped)\s+(?:one\s+or\s+more|at\s+least\s+(?:one|\d+)|\d+)"
    r"[\w\s]{0,30}?(?:apps?|applications?)\b|"
    r"\bpublished\s+apps?\b|"
    r"(?:apps?|applications?)\s+(?:already\s+)?published\s+(?:on|in|to|through)\b|"
    r"(?:track\s+record|proven\s+track\s+record|history)\s+of\s+(?:having\s+)?"
    r"(?:successfully\s+)?(?:publish(?:ed|ing)|shipp?(?:ed|ing)|launch(?:ed|ing)|releas(?:ed|ing))\b|"
    r"(?:track\s+record|history|proven)\s+of\s+at\s+least\s+(?:one|\d+)\s+"
    r"(?:live\s+|production\s+)?(?:apps?|applications?)\b|"
    r"(?:google\s+play|app\s+store|play\s+store)\s+(?:published|publicad|public)|"
    # Orden invertido ES/PT: "al menos una app publicada", "app publicada en
    # Google Play", "Experiencia com publicacao de aplicativos na Google Play
    # Console" (caso TCS 4476935001). El patron anterior exigia el nombre de la
    # tienda ANTES de "published/publicad", asi que Start Companies (2026-10-09)
    # pedia una app publicada y daba PASS con 0 hallazgos.
    r"(?:al\s+menos|m[íi]nimo|por\s+lo\s+menos|ao\s+menos|pelo\s+menos)\s+"
    r"una?\s+(?:app|aplicaci[óo]n|aplicativo|juego|game)s?\s+publicad[oa]s?\b|"
    r"(?:app|aplicaci[óo]n|aplicativo)s?\s+publicad[oa]s?\s+(?:en|em|na|no)\s+"
    r"(?:google\s+play|app\s+store|play\s+store)\b|"
    r"publicad[oa]s?\s+(?:en|em|na|no)\s+"
    r"(?:google\s+play|app\s+store|play\s+store)\b|"
    r"(?:experi[êe]ncia|experience)\s+com\s+publica[çc][ãa]o|"
    # Orden "publicacao ... na App Store/Google Play" y "ciclo de publicacao"
    # (caso IT Singular 2026-10-09). El regex solo miraba el orden
    # "tienda + published".
    r"publica[çc][ãa]o[^\n]{0,40}?(?:google\s+play|app\s+store|play\s+store)\b|"
    r"(?:ciclo|processo)\s+(?:completo\s+)?de\s+publica[çc][ãa]o\b",
    re.I,
)

# --- F13: stack ajena declarada como requisito FUNDAMENTAL/obligatorio -----
# F6 solo cuenta dominancia por numero de menciones; una vacante puede nombrar
# PHP/Laravel pocas veces y aun asi exigirlo como pilar. Caso IT Singular
# (2026-10-09): "Dominio em PHP, requisito fundamental para a posicao" daba
# PASS con 0 hallazgos (Flutter tambien estaba, como segunda pata full-stack).
# Solo dispara si el marcador duro ("requisito/fundamental/excluyente...") esta
# pegado al stack ajeno, para no rechazar roles donde el stack es un adorno.
RE_STACK_OBLIG = re.compile(
    r"(?:dom[íi]nio|dom[ií]nio|experi[êe]ncia|conhecimento|conocimiento|"
    r"capacidade|capacidad|viv[êe]ncia)\s*"
    r"(?:em|en|com|de|no|na|s[óo]lid[oa]\s+em)?\s*"
    r"(php|laravel|java|spring(?:\s*boot)?|\.net|c#|kotlin|swift|"
    r"ruby(?:\s*on\s*rails)?|node\.?js|angular|react\s*native)\b"
    r"[^\n]{0,60}?"
    r"(requisito|obrigat[óo]ri[oa]|excluyente|fundamental|imprescind[íi]vel|"
    r"obligatori[oa]|indispens[áa]vel|essencial)",
    re.I,
)

# --- F7: inglés duro (AVISO, no descarte — precedente Altimetrik) --------
RE_INGLES_HARDO = re.compile(
    r"(ingl[êe]s\s+avan[çc]ado|advanced\s+english|fluent\s+english|"
    r"business\s+english|full\s+professional\s+proficiency|"
    r"written\s+and\s+verbal\s+fluency|b2\s*/\s*c1|b2\s*\+|"
    r"ingl[êe]s\s+fluente|ingl[êe]s\s+t[ée]cnico\s+avanzado)",
    re.I,
)

# --- F6: stacks que compiten con Flutter ---------------------------------
STACKS_AJENAS = {
    "react native": r"react\s*native",
    "kotlin/compose": r"\bkotlin\b|jetpack\s*compose",
    "swift/ios nativo": r"\bswift(ui)?\b|objective-?c",
    ".NET / C#": r"\b(c#|\.net|dotnet|asp\.net)\b",
    "java/spring": r"\bjava\b|spring\s*boot|\bspring\b",
    # PHP/Laravel: 0 menciones en la base del usuario. Un rol full-stack que
    # exige PHP como pilar no es un rol Flutter con PHP de adorno.
    "php/laravel": r"\bphp\b|\blaravel\b",
    "data engineering": r"\bdatabricks|unity\s+catalog|pyspark|delta\s+lake|"
                        r"\bdataops\b|data\s+engineering|airflow|dbt\b|"
                        r"spark\b|etl\b",
    "QA/automation": r"\bselenium\b|cypress|playwright|appium|test\s+automation",
    "ML/AI research": r"\bmachine\s+learning\b|pytorch|tensorflow|\bmlops\b",
}
# Angular no esta en la base del usuario (0 menciones). Un rol de web con
# Angular como framework declarado no es un rol Flutter con angular de adorno.
RE_ANGULAR = re.compile(r"\bangular\b", re.I)
# Frameworks web que si implican rol web-perfil -> Flutter queda secundario.
# (React/Next.js se excluyen aqui a proposito: si el rol es puramente React,
# lo cubre F11 por conteo, no esta regla.)
RE_WEB_PERFIL = re.compile(
    r"\bvue(?:\.js)?\b|\breact\s*native\b|\bnext\.js\b|\btypescript\b|\bnpm\b",
    re.I,
)

RE_ANIOS = re.compile(r"(\d{1,2})\s*\+?\s*(?:\+)?\s*years?", re.I)
RE_ANIOS_PT = re.compile(r"(\d{1,2})\s*\+?\s*(?:\+)?\s*anos", re.I)


def _cuenta(patron, texto):
    """Cuenta ocurrencias. Acepta patron compilado o string."""
    if hasattr(patron, "finditer"):
        return sum(1 for _ in patron.finditer(texto))
    return len(re.findall(patron, texto, re.I))


def evaluar(titulo, empresa, cuerpo):
    """Devuelve (veredicto, lista_de_hallazgos). veredicto in {PASS, FAIL}."""
    texto = cuerpo or ""
    hay = []

    def reject(regla, msg):
        hay.append(("reject", regla, msg))

    def warn(regla, msg):
        hay.append(("warn", regla, msg))

    # F1 — Flutter/Dart ausente por completo
    if not RE_FLUTTER.search(texto):
        stacks = ", ".join(
            k for k, p in STACKS_AJENAS.items() if _cuenta(p, texto) >= 2
        )
        reject(
            "F1",
            f"Flutter/Dart aparece 0 veces en el cuerpo. "
            f"Stack real de la vacante: {stacks or 'no identificado'}.",
        )
    else:
        # F2 — Flutter aparece, pero solo tras un marcador de "deseable"
        corte = RE_DESEJABLE.search(texto)
        primero = RE_FLUTTER.search(texto)
        if corte and primero and primero.start() > corte.start():
            reject(
                "F2",
                "Flutter aparece unicamente despues de un marcador de "
                "'deseable/nice to have/plus' -> no es requisito base.",
            )

    # F3 — nivel inaccesible
    if RE_NIVEL_ALTO.search(titulo or ""):
        reject(
            "F3",
            f"Titulo de nivel alto para {NIVEL_ESPERADO} "
            f"({ANIOS_SW}+ años): '{RE_NIVEL_ALTO.search(titulo).group(0)}'.",
        )

    # F4 — presencial declarado sin remoto que lo compense
    if RE_CONTRATO_LOCAL.search(texto) and not RE_REMOTO.search(texto):
        m = RE_CONTRATO_LOCAL.search(texto)
        reject(
            "F4",
            f"Presencial/contrato local declarado y sin 'remoto': "
            f"'{m.group(0).strip()}'.",
        )

    # F5 — formación completa obligatoria
    m = RE_FORMACION_OBLIG.search(texto)
    if m:
        reject(
            "F5",
            f"Exige formacion superior COMPLETA (tu bachelor sigue en "
            f"curso, bloqueante D-08): '{m.group(0).strip()}'.",
        )

    # F6 — stack ajena domina el cuerpo
    counts = {k: _cuenta(p, texto) for k, p in STACKS_AJENAS.items()}
    ajena, n = max(counts.items(), key=lambda kv: kv[1]) if counts else ("", 0)
    if n >= 4:
        reject(
            "F6",
            f"'{ajena}' domina la vacante ({n} menciones) frente a "
            f"Flutter ({_cuenta(RE_FLUTTER, texto)}).",
        )

    # F10 — Angular declarado (el usuario no lo tiene: 0 en su base)
    n_ang = _cuenta(RE_ANGULAR, texto)
    if n_ang >= 2:
        reject(
            "F10",
            f"Angular aparece {n_ang} veces y no esta en tu base. "
            f"Es un rol de web con Angular como framework, no Flutter.",
        )

    # F11 — el perfil web supera a Flutter en el cuerpo
    n_web = _cuenta(RE_WEB_PERFIL, texto)
    n_flut = _cuenta(RE_FLUTTER, texto)
    if n_web >= 3 and n_web > n_flut:
        reject(
            "F11",
            f"Señales de perfil web ({n_web} menciones de frameworks/"
            f"herramientas web) superan a Flutter ({n_flut}). "
            f"Flutter es secundario en esta vacante.",
        )

    # F12 — exige app movil ya publicada en tienda (imposible por veracidad)
    m_pub = RE_APP_PUBLICADA.search(texto)
    if m_pub:
        reject(
            "F12",
            f"Exige app movil YA publicada en Google Play / App Store: "
            f"'{m_pub.group(0).strip()[:60]}'. Tu CV base prohibe afirmar publicacion "
            f"(regla de veracidad #5) y Rifame sigue sin publicar (O-01): "
            f"no se puede cumplir sin mentir.",
        )

    # F13 — stack ajena exigida como requisito fundamental
    m_ob = RE_STACK_OBLIG.search(texto)
    if m_ob:
        reject(
            "F13",
            f"Una stack ajena se exige como requisito fundamental: "
            f"'{m_ob.group(0).strip()[:60]}'. Tu base no la tiene (0 menciones): "
            f"es un rol full-stack, no un rol Flutter con ese stack de adorno.",
        )

    # --- avisos (no descartan) --------------------------------------------
    if RE_INGLES_HARDO.search(texto):
        m = RE_INGLES_HARDO.search(texto)
        warn("F7", f"Ingles demanding: '{m.group(0).strip()}' (tu B1, D-09).")

    if RE_NIVEL_BAJO.search(titulo or ""):
        warn("F8", "Titulo Junior: quedarias por encima del nivel pedido.")

    años = [int(x) for x in RE_ANIOS.findall(texto) + RE_ANIOS_PT.findall(texto)]
    if años and max(años) > ANIOS_SW + 4:
        warn("F9", f"Pide hasta {max(años)}+ años (tienes {ANIOS_SW}+).")

    veredicto = "FAIL" if any(n == "reject" for n, _, _ in hay) else "PASS"
    return veredicto, hay


def _leer(args):
    if args.archivo:
        with open(args.archivo, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    if args.stdin or not args.texto:
        return sys.stdin.read()
    return args.texto


def main():
    ap = argparse.ArgumentParser(description="Pre-filtro de vacantes Flutter.")
    ap.add_argument("--titulo", required=True)
    ap.add_argument("--empresa", default="")
    ap.add_argument("--archivo")
    ap.add_argument("--texto")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--marcar", action="store_true",
                    help="Si FAIL, marca la vacante como descartado en el historial.")
    args = ap.parse_args()

    veredicto, hall = evaluar(args.titulo, args.empresa, _leer(args))

    if args.json:
        print(json.dumps({
            "veredicto": veredicto,
            "titulo": args.titulo,
            "empresa": args.empresa,
            "hallazgos": [{"severidad": s, "regla": r, "motivo": m} for s, r, m in hall],
        }, ensure_ascii=False, indent=2))
    else:
        marca = {"reject": "RECHAZA", "warn": "aviso "}[hall[0][0]] if hall else "ok"
        print(f"{marca}  {args.empresa} — {args.titulo}  [{veredicto}]")
        for sev, regla, mot in hall:
            print(f"  [{regla}] {mot}")

    if args.marcar and veredicto == "FAIL":
        from tracker import Historial, vacancy_key  # noqa: PLC0415
        h = Historial(HISTORIAL_PATH)
        key = vacancy_key(args.empresa, args.titulo)
        h.add("vacantes", key, {"titulo": args.titulo, "empresa": args.empresa,
                                "url": args.archivo if args.archivo.startswith("http") else None,
                                "motivo": ", ".join(r for _, r, _ in hall)})
        h.set_state("vacantes", key, "descartado")
        print(f"\n  -> historial: vacantes/{key} = descartado")

    return 0 if veredicto == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
