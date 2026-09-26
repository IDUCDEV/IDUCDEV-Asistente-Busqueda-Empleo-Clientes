# LinkedIn — texto listo para pegar (INGLÉS)

> Generado 2026-09-26 desde `recursos/cv/base-isaac-urdaneta.md`.
> Texto plano: **sin markdown**, se pega tal cual.
> Si un dato discrepa, el base manda. No pegues nada sin leer la nota
> de verificación del final.

> Cuándo usar este archivo en vez del español: cuando el objetivo sea
> vacantes en US, Canadá o Europa. LinkedIn tiene **un solo campo About**,
> así que no puedes tener los dos a la vez. Cambiar de idioma es gratis y
> se hace en 30 segundos: úsalo según la vacante que estés persiguiendo.

---

## 1. HEADLINE

Copy this into the *Headline* field (LinkedIn limit: 220 characters; this
one is 72).

```
Flutter Engineer | Clean Architecture, FPdart & Supabase | Scalable Apps
```

Alternatives, only if you change target:

```
Flutter Engineer & DevOps | Docker, CI/CD | Supabase
```
```
Frontend & Mobile Engineer | Flutter, Next.js, TypeScript
```

> The headline is in English keywords on purpose: that's how recruiters
> search and how LinkedIn's own search indexes you. Switching it to
> Spanish reduces who finds you.

---

## 2. ABOUT

Paste the whole block into the *About* field (limit: 2,600 characters; this
one is 1,162).

```
Flutter Engineer with 2+ years in Flutter and 3+ years in software development. I started in web frontend (React, Next.js, TypeScript) and specialised in Dart and Flutter, building applications with Clean Architecture and Functional Programming (FPdart).

At IDUCDEV I design and ship complete products end to end. Rifáme (raffle management) is in public beta with 100+ real participants, 3 active raffles and a track record of 5 versioned releases (v1.0.0 → v1.0.2). In SereniFlu I built an emotional mapping engine with 94% accuracy, validated against a test case set.

My approach goes beyond code: I bring DevOps into mobile development (Docker, Makefiles, GitHub Actions) and manage the release cycle with my own distribution channel. Tests with mocktail, bloc_test and integration_test, plus integration against a local Supabase instance.

Open technical guide to Clean Architecture with Flutter and Supabase, across 25 public repositories of my own code.

Stack: Flutter, Dart, Clean Architecture, FPdart, BLoC/Cubit, GetIt, GoRouter, Supabase, PostgreSQL (RLS), Next.js, TypeScript, Tailwind CSS. UTC-4 · available for EST/PST overlap.

iducdev.org · github.com/IDUCDEV · youtube.com/@iducdev
```

---

## 3. EXPERIENCE

LinkedIn is not a free-text field: every role has separate boxes. Fill in
each block as shown.

### 3.1 — Mobile Engineer · IDUCDEV

| LinkedIn field | Value |
|---|---|
| Job title | Mobile Engineer |
| Company | IDUCDEV (freelance / own product) |
| Dates | Jul 2025 – Present |
| Location | Remote (UTC-4) |
| Type | Employment |

**Description:**

```
• Developed and shipped Rifáme, a Flutter raffle management app in public beta: 100+ real participants, 3 active raffles and 5 versioned releases (v1.0.0 → v1.0.2) on my own distribution channel.
• Implemented temporary number reservation with automatic expiry and release, plus a live sales counter via Supabase Realtime.
• Designed a modular clean architecture that allows swapping the backend at runtime by configuration (Supabase ↔ REST API).
• Built SereniFlu's emotional mapping engine at 94% accuracy, validated against a test case set.
• Unit and widget tests with mocktail and bloc_test, plus integration tests against a local Supabase instance.
• Built a toolchain with Makefiles and Docker that cut development environment setup time.
• Integrated Supabase auth, Row Level Security and real-time sync on PostgreSQL.
```

> Do not write "published on Google Play" or "on the App Store". It's beta
> with your own channel. If asked, the honest and favourable answer is
> "5 versioned releases, 100+ real users, own distribution".

### 3.2 — Frontend Developer · Ayuntamiento de Buchivacoa

| LinkedIn field | Value |
|---|---|
| Job title | Frontend Developer |
| Company | Ayuntamiento de Buchivacoa |
| Dates | Feb 2025 – Jun 2025 |
| Location | Venezuela |
| Type | Employment |

**Description:**

```
• Built 8 interface screens for the institutional site, including news, contact forms and responsive design.
• Implemented Server-Side Rendering in Next.js, improving load time over the previous version.
• Established a frontend style guide and best practices, documented and adopted by the team.
```

> The "+25% maintainability" figure was removed: it wasn't measurable.
> The style guide replaces it, because it's a checkable fact.

### 3.3 — Frontend & Mobile Developer · No Country

| LinkedIn field | Value |
|---|---|
| Job title | Frontend & Mobile Developer |
| Company | No Country |
| Dates | Jan 2023 – Jan 2025 |
| Location | Remote |
| Type | Employment |

**Description:**

```
• Shipped 7+ cross-platform solutions with React, TypeScript and Flutter within an agile team.
• Reduced API response times through caching, code-splitting and payload optimisation.
• Worked on accessibility (Lighthouse) across client projects.
```

> The percentages (35% API, Lighthouse 98) were removed on purpose: how
> they were measured isn't confirmed. If a recruiter asks, give the
> method, not the bare number.

---

## 4. SKILLS

LinkedIn doesn't accept a paste: you search and add them one by one. These
are the 10 that filter hardest, in this order (LinkedIn shows the 10 with
the most endorsements, so load order doesn't decide final order —
endorsements do):

```
Flutter
Dart
Clean Architecture
FPdart
BLoC
Cubit
Supabase
mocktail
bloc_test
PostgreSQL
```

Then, as your own skills without endorsements: Unit Testing, Integration
Testing, Widget Testing, Row Level Security, Docker, Docker Compose, GitHub
Actions, CI/CD, Makefile, Bash, Linux, GetIt, GoRouter, REST APIs,
WebSockets, Functional Programming, Next.js, TypeScript, React.js,
Tailwind CSS, SOLID, DevOps, Figma, RxDart, Provider, Dokploy, Git.

**Do not add** Riverpod, Serverpod, push notifications, offline support or
Google/Apple auth: they're advertised on `iducdev.org` but unconfirmed.

---

## 5. VERIFY BEFORE PUBLISHING

- [ ] **Dates and locations** checked against your real profile. The ones
      above come from the base; if LinkedIn shows different ones, fix those
      first.
- [ ] Company names typed exactly as you have them.
- [ ] The headline fits in 72 characters. If you edit and exceed 220,
      trim it.
- [ ] The About fits in 2,600. It's 1,162: plenty of room.
- [ ] You picked **one** About language. For LATAM use
      `linkedin-pegar-es.md` instead of this file.
- [ ] No line claims store publication (rule R2).
- [ ] No skill says "Expert" (rule R3).
- [ ] No percentages without a measurement method.

### Data verified against GitHub (2026-09-26)

| Fact | Real value |
|---|---|
| Public repos | 25 |
| Dart repos | 5 |
| Forks | 2 (both in `clariFi`) |
| Stars | 4 |

That's why the About **doesn't** quote stars or forks: the numbers are weak,
and in an earlier version of this guide they were published wrong
("0 forks"). The GitHub fact that does appear is the 25 repos, which is
correct.
