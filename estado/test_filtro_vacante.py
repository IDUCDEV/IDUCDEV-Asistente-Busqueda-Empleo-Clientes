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

PAGINAS = "/home/iducdev/.local/share/opencode/tool-output"

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
    """Acepta ruta a archivo, texto inline, o None (fixture de Hansa)."""
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
        )
    if "\n" in fuente or " " in fuente and not os.path.exists(fuente):
        return fuente  # texto inline
    with open(fuente, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _main():
    fallos = 0

    print("=== DESCARTAS (deben dar FAIL) ===")
    for titulo, empresa, path, regla_esperada in DESCARTES:
        cuerpo = _cargar(path)
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

    total = len(DESCARTES) + len(ACEPTADAS)
    print(f"\n{total - fallos}/{total} correctos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(_main())
