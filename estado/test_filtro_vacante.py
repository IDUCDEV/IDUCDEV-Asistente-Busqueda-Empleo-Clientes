#!/usr/bin/env python3
"""test_filtro_vacante.py — Regresión del pre-filtro.

Casos reales que motivaron el filtro:
  DESCARTAS  Hansa (presencial La Paz), Walmart (Principal 9+ años),
            QiBit (Flutter ausente), Mars (data engineering)
  ACEPTADAS Altimetrik, Rethink, Iterative  (las 3 que generaron CV)

Los 4 descartes usan el HTML real descargado de LinkedIn.
Las 3 aceptadas usan extractos con los requisitos confirmados en sesion.

    python3 estado/test_filtro_vacante.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from filtro_vacante import evaluar  # noqa: E402

# Los 4 casos marcados con ruta leen el HTML real que descargué de LinkedIn
# durante la sesión de análisis. Esos volcados viven en la caché local de
# opencode, que NO es parte del repo y solo existe en la máquina donde se hizo
# el scraping. Se resuelve por entorno (nunca con una ruta absoluta hardcodeada,
# regla de oro #1) y, si no está, esos casos se marcan SKIP en vez de romper el
# archivo: los casos con texto inline se siguen ejecutando siempre.
PAGINAS = os.environ.get(
    "IDUCDEV_FIXTURES",
    os.path.join(
        os.environ.get("XDG_DATA_HOME",
                       os.path.expanduser("~/.local/share")),
        "opencode", "tool-output",
    ),
)

DESCARTES = [
    (
        "Senior Android Developer - Híbrido em Campinas",
        "QiBit",
        f"{PAGINAS}/tool_1024dfec5001OE6dA2h6KTlwgO",
        "F4",
    ),
    (
        "Principal Software Engineer",
        "Walmart Global Tech",
        f"{PAGINAS}/tool_102439b76001ygSj0PK0YSOkFE",
        "F3",
    ),
    (
        "DataOps Engineer",
        "Mars",
        f"{PAGINAS}/tool_102511767001ns8VZQ2AA1HhtB",
        "F1",
    ),
    (
        "Desarrollador Móvil Junior",
        "Hansa Ltda",
        None,
        "F2",
    ),
    (
        "Desarrollador de front-end",
        "Tata Consultancy Services",
        """
Tata Consultancy Services (TCS) busca un Desarrollador Frontend con experiencia
en desarrollo web moderno y capacidades en mobile.
Responsabilidades: Desarrollo y mantenimiento de aplicaciones frontend modernas.
Construcción de interfaces dinámicas utilizando Angular, TypeScript y JavaScript.
Gestión de datos en cliente mediante caching y LocalStorage.
Administración de dependencias y paquetes con NPM.
Desarrollo de aplicaciones móviles con Flutter.
Integración de soluciones frontend con servicios en la nube (AWS).
Requisitos: Formación en Ingeniería de Sistemas o carreras afines.
Experiencia mínima de 3 años como desarrollador frontend.
Lenguajes: TypeScript, JavaScript. Framework: Angular. Mobile: Flutter.
Manejo de estado/datos: Caching, LocalStorage. Gestión de dependencias: NPM. Cloud: AWS.
Habilidades clave: Fundamentos CSS, Angular, JavaScript, React.
Modalidad: Híbrido (Medellín y Bogotá - 3 días presencial); Remoto (otras ciudades).
""",
        "F10",
    ),
    (
        # Regresion 2026-10-04:Engesoftware (br.linkedin.com). El filtro daba
        # PASS con 0 hallazgos porque F5 solo tenia patrones ES/EN y la vacante
        # pide "Ensino superior TI concluido". Exigia ademas 5 anos (tiene 3).
        "Desenvolvedor Flutter Pleno",
        "ENGESOFTWARE Tecnologia",
        """
DESENVOLVEDOR FLUTTER PLENO - ENGESOFTWARE TECNOLOGIA S.A.
Experiência - Mínimo de 5 anos comprovados em desenvolvimento de software Mobile
Flutter + Dart em nível avançado
Flutter Bloc, Cubit ou Provider; APIs assíncronas; ciclo de vida do app;
plugins/pacotes customizados
Web React + TypeScript
Framework web Next.js, incluindo App Router
Front-end Vanilla CSS e Tailwind
UX/UI Figma, componentes reutilizáveis, responsividade e WCAG
Integrações REST e GraphQL
Segurança OAuth2, OIDC, JWT, MFA, SSL Pinning e ofuscação
Testes mobile Testes unitários, de widget e integração em Flutter
Testes web Jest, Cypress e/ou Playwright
Certificação Conhecimento
Ensino superior TI concluído;
5 anos de experiência na area
Remoto
Benefícios Assistência Médica / Medicina em grupo Assistência Odontológica
Estudo de faculdade Ticket alimentação Tícket refeição Vale-transporte
Horário de Trabalho Horário comercial, de segunda a sexta.
""",
        "F5",
    ),
    (
        # Mismo hueco de F5 en PT, variante "Superior Completo (Pleno)".
        "Desenvolvedor Flutter Sênior",
        "Rhexis Consultoria",
        """
Vaga: Desenvolvedor Flutter Sênior. Remoto, home office.
Requisitos: 4+ anos com Flutter e Dart; BLoC/Cubit; APIs REST;
publicação em Google Play e App Store.
Formação: Superior Completo (Pleno) em Ciência da Computação ou áreas correlatas.
Inglês avançado para leitura de documentação técnica.
Contratação PJ,home office com possibilidade de híbrido em Belo Horizonte.
""",
        "F5",
    ),
    (
        # Regresion 2026-10-04: F3 no conocía los cargos jerárquicos de PT-BR.
        "Coordenador de Desenvolvimento Flutter",
        "Vitau Tecnologia",
        """
Coordenador(a) de Desenvolvimento Flutter em Belo Horizonte.
Responsável por liderança técnica do time mobile (Flutter/Dart),
arquitetura, code review e mentoria de devs.
Requisitos: 6+ anos de experiência, 3+ liderando times;
Formação superior completa; Inglês avançado.
Contratação CLT, regime presencial.
""",
        "F3",
    ),
    (
        # Regresion 2026-10-04 (segunda tanda): F4 no sabia leer la etiqueta de
        # jornada que LinkedIn/Indeed muestran suelta en la tarjeta ("Presencial").
        # Antes solo entendia la frase espanola; esta vacante es on-site en Brasilia
        # con salario en BRL y se colaba. Bloquea por F4 (presencial) y F5 (grado).
        "Desenvolvedor Flutter Senior",
        "Engesoftware Tecnologia S.A.",
        """
DESENVOLVEDOR FLUTTER SENIOR - Engesoftware Tecnologia S.A.
Local: Brasilia, Distrito Federal, Brasil
Modalidade: Presencial
Tipo de emprego: Jornada completa (Tempo integral)
Nivel de experiencia: Pleno-senior
Faixa salarial base: R$ 8.500,00 por mes - R$ 8.500,00 por mes
Desenvolvedor Flutter com responsabilidade em estimar esforco de demandas,
implementar funcionalidades de software, planejar e implementar testes
unitarios e automatizados, correto uso de Git.
Certificacao Conhecimento
Ensino superior TI concluido;
3 anos de experiencia na area;
Beneficios Assistencia Medica / Medicina em grupo Assistencia Odontologica
Estudo de faculdade Ticket alimentacao Ticket refeicao Vale-transporte
Horario de Trabalho A combinar.
""",
        "F4",
    ),
    (
        # Regresion 2026-10-04 (tercera tanda): el patron ES de F5 estaba MUERTO.
        # Decia "forma[çc][ãa]o" y en espanol la palabra es "formacion" (o tilde),
        # no "formacao" (a tilde). "Formacion superior completa" NUNCA matcheo, que
        # es justo el caso base de F5 en el idioma principal del mercado objetivo.
        "Desarrollador Flutter Senior",
        "Consultora Andina",
        """
Buscamos Desarrollador Flutter Senior para producto fintech.
Modalidad: Remoto (LATAM).
Requisitos: 5+ anos con Flutter y Dart; Clean Architecture; BLoC/Cubit;
Supabase/Firebase; pruebas automatizadas.
Formacion superior completa en Ingenieria de Sistemas o areas correlatas.
Ingles intermedio.
""",
        "F5",
    ),
    (
        # Regresion 2026-10-04 (tercera tanda): F5 exigeia "concluido" y la vacante
        # dice "Conclusao de nivel superior" (sustantivo, orden invertido). Daba PASS
        # con nivel superior OBLIGATORIO. Es la 3ra vacante del mismo cluster BR.
        "Desenvolvedor front-end Flutter/Dart",
        "Engesoftware Tecnologia S.A.",
        """
Estamos em busca de um Desenvolvedor front-end Flutter/Dart para compor o nosso time!
Essa vaga inclui Pessoas com Deficiência - PCD
VA ou VR; Plano de saúde; Plano odontológico (Bradesco);
Descontos exclusivos com (SENAC, Anhanguera, Estácio, IESB, Cruzeiro do Sul).
Obrigatório:
Conclusão de nível superior ou pós-graduação em TI.
Experiência mínima de 5 anos.
Conhecimentos Exigido:
Experiência avançada com Flutter e Dart;
Conhecimento em Bloc, Cubit ou Provider;
Experiência com React, TypeScript e Next.js;
Conhecimento em CSS, Tailwind e Figma;
Experiência com integrações REST e GraphQL;
Conhecimentos em segurança e autenticação (OAuth2, OIDC, JWT);
Experiência com testes em Flutter e aplicações Web.
""",
        "F5",
    ),
    (
        # Regresion 2026-10-04 (cuarta tanda): exige app movil YA publicada, que el
        # CV base prohibe afirmar (veracidad #5) y O-01 confirma pendiente. Match
        # tecnico casi perfecto (3+ anos exactos, Bloc/Cubit, Firebase) y aun asi
        # es imposible sin mentir -> bloqueante. Nueva regla F12.
        "Senior Flutter Developer",
        "Jobgether",
        """
This position is listed on behalf of a partner company. Our partner is looking for
a Senior Flutter Developer based in Brazil. Fully remote contract setting.
Requirements
Flutter & Dart Expertise: Proven hands-on experience in mobile application development
using the Flutter framework and Dart, backed by 3+ years of overall software development.
Published Applications: Demonstrated track record of having published one or more live
mobile applications on the Google Play Store or Apple App Store.
Agile & Lifecycle Mastery: state management techniques, and automated building/testing.
Preferred: cloud services (Firebase, AWS Amplify, GCP), CI/CD, RESTful web services.
Benefits
100% Remote Flexibility: Complete location independence.
Contract Autonomy: self-directed contract engagement.
""",
        "F12",
    ),
]

ACEPTADAS = [
    (
        "Senior Flutter Developer (Remote)",
        "Altimetrik",
        """
Senior Flutter Developer - Remote (LATAM). 100% remoto.
Requirements: 5+ years of professional experience in software development,
strong Flutter and Dart skills, English B2+/C1 (advanced).
Solid knowledge of state management (BLoC, Provider), REST APIs,
CI/CD, Git, unit and widget testing. Google Play Store publishing experience.
Responsibilities: design and build high-quality mobile applications,
architectural decisions, code reviews, mentor junior developers.
Remote-first team, contractor, available immediately.
""",
    ),
    (
        "Desenvolvedor(a) Flutter - Sênior",
        "Rethink by Framework",
        """
Vaga: Desenvolvedor(a) Flutter - Sênior. 100% remoto.
Requisitos: experiência sólida em desenvolvimento Flutter e Dart;
conhecimento em Clean Architecture, SOLID, BLoC/RxDart;
APIs REST e integração com backends; Git e fluxo colaborativo;
testes automatizados;元以上 CI/CD.
Inglês avançado ou fluente.，而后 Spanish/Portuguese.
Atuação remota, contrato PJ, disponível imediatamente.
""",
    ),
    (
        "Desenvolvedor Mobile Sênior",
        "Iterative;",
        """
Vaga: Desenvolvedor Mobile Sênior. Atuação 100% remoto.
Requisitos: React Native; Flutter; Android ou iOS; Firebase; APIs REST;
Testes mobile. Contratação PJ, 6 meses, com possibilidade de prorrogação.
Atividades: cerimônias ágeis e revisões de código; qualidade, performance e
documentação técnica; evolução contínua da plataforma.
Não exige inglês. Semipresencial nunca é mencionado.
""",
    ),
]


def _cargar(fuente):
    """Acepta ruta a archivo, texto inline, o None (fixture de Hansa).

    Devuelve (texto, disponible). `disponible=False` significa que el fixture es
    un HTML descargado que no está en esta máquina: el caso se salta.
    """
    if fuente is None:
        return (
            "Requisitos: 6 meses a 1 año de experiencia en desarrollo móvil.\n"
            "Android/Kotlin con Jetpack Compose (sólido conocimiento), MVVM, SQLite.\n"
            "Conocimientos Valorados (Deseables): Flutter, Dart, KMP, NestJS, "
            "MongoDB, Firebase.\n"
            "Si cumples los requisitos, tienes base en la ciudad de La Paz y "
            "deseas ser parte de una empresa de software.\n"
            "Presentar garantías reales (Letra). Inglés intermedio o superior "
            "(enfocado en lectura técnica).\n"
        ), True
    if "\n" in fuente or (" " in fuente and not os.path.exists(fuente)):
        return fuente, True  # texto inline
    if not os.path.exists(fuente):
        return "", False  # fixture externo ausente en esta máquina
    with open(fuente, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read(), True


def _main():
    fallos = 0
    saltados = 0

    print("=== DESCARTAS (deben dar FAIL) ===")
    for titulo, empresa, path, regla_esperada in DESCARTES:
        cuerpo, disponible = _cargar(path)
        if not disponible:
            saltados += 1
            print(f"  [SKIP] {empresa:20} falta el HTML descargado "
                  f"(apunta IDUCDEV_FIXTURES)")
            continue
        v, hall = evaluar(titulo, empresa, cuerpo)
        reglas = {r for s, r, _ in hall if s == "reject"}
        ok = v == "FAIL" and regla_esperada in reglas
        fallos += 0 if ok else 1
        print(f"  [{'OK ' if ok else 'FALLA'}] {empresa:20} {v:5} "
              f"reglas={sorted(reglas)} (esperaba {regla_esperada})")

    print("\n=== ACEPTADAS (deben dar PASS) ===")
    for titulo, empresa, cuerpo in ACEPTADAS:
        v, hall = evaluar(titulo, empresa, cuerpo)
        ok = v == "PASS"
        fallos += 0 if ok else 1
        warns = [f"{r}" for s, r, _ in hall if s == "warn"]
        print(f"  [{'OK ' if ok else 'FALLA'}] {empresa:20} {v:5} avisos={warns}")

    total = len(DESCARTES) + len(ACEPTADAS) - saltados
    print(f"\n{total - fallos}/{total} correctos")
    if saltados:
        print(f"({saltados} caso(s) omitidos: falta el HTML descargado)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(_main())
