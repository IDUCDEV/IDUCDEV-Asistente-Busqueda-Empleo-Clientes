# Optimización de LinkedIn — Isaac Urdaneta

> Perfil objetivo: linkedin.com/in/isaac-urdaneta
> Última regeneración: **2026-09-26**

---

## AVISO DE PROCEDENCIA

**Este documento es derivado.** Se genera desde
`recursos/cv/base-isaac-urdaneta.md` y sus cifras no son fuente de verdad.

- Si un dato discrepa entre este archivo y el base, **manda el base**.
- Antes de usar cualquier cifra de aquí, comprobar que sigue en el base.
- Al cambiar los datos del base, regenerar este archivo.
- Aplica además las reglas de integridad R1-R6 de
  `recursos/guias/cv-reglas-ats.md`.

**Cambios de esta regeneration respecto a la versión de junio 2026:**

| Antes (incorrecto) | Ahora |
|---|---|
| "1 año de experiencia en Flutter" | **2+ años en Flutter, 3+ en software** |
| "3+ aplicaciones Flutter publicadas a producción" | 1 app en **beta pública** con canal propio; ninguna en Play Store ni App Store |
| "mantenibilidad +25%" | **guía de estilo documentada y adoptada** (sin número) |
| Sin métricas de tracción | **100+ usuarios reales**, **5 releases** |
| Métrica de GitHub con dato erróneo ("0 forks") | Fuera del About: 4 stars y 2 forks no son una señal (O-02); se cita el repo de la guía |
| Sin stack de testing | **mocktail, bloc_test, integration_test** |
| Sin experiencia web | **Next.js, TypeScript, Tailwind** — 3 años de trayectoria web |
| 94% sin proyecto ni método | **SereniFlu**, validado contra un set de casos de prueba |

---

## 1. HEADLINE (Titular)

### Estado actual por comprobar
```
Flutter Developer | Mobile Engineer | Dart, Supabase & Clean Architecture | Systems Engineer
```
84 caracteres. Si ya lo cambiaste, actualizar esta línea.

### Diagnóstico
- Redundancia: "Flutter Developer" y "Mobile Engineer" son el mismo rol
- "Systems Engineer" es el título académico, no el rol profesional
- Le falta una propuesta de valor, no sólo keywords

### Opciones (≤120 caracteres)

| # | Titular | Caracteres | Cuándo |
|---|---------|-----------|--------|
| 1 | `Flutter Engineer \| Clean Architecture, FPdart & Supabase \| Scalable Apps` | **72** ✅ | **por defecto** (variante T1 del base) |
| 2 | `Flutter Engineer & DevOps \| Docker, CI/CD \| Supabase` | 52 | vacantes DevOps/infra (variante T2) |
| 3 | `Frontend & Mobile Engineer \| Flutter, Next.js, TypeScript` | 57 | vacantes web/fullstack (variante T3) |

**Recomendada: opción 1.** Rol + keywords técnicas + propuesta de valor.
FPdart es lo que le diferencia del perfil Flutter medio; Supabase cubre
otra keyword muy buscada.

> El titular **no cambia** por vacancy: hay un solo perfil. Para adaptar el
> CV a una vacante se usa la variante del base (sección 2), no el titular.

---

## 2. ABOUT (Acerca de)

### Diagnóstico del estado anterior
Sin métricas de tracción, sin FPdart en el headline, sin conectar
DevOps con mobile, y con una afirmación falsa de publicación en stores.

### Texto propuesto — ESPAÑOL

> Flutter Engineer con **2+ años en Flutter y 3+ años en desarrollo de
> software**. Empecé en frontend web (React, Next.js, TypeScript) y me
> especialicé en Dart y Flutter, construyendo aplicaciones con **Clean
> Architecture** y **Programación Funcional (FPdart)**.
>
> En IDUCDEV desarrollo y publico productos completos de principio a fin.
> **Rifáme** (gestión de rifas) está en **beta pública** con **más de 100
> participantes reales**, 3 rifas activas y un historial de **5 releases
> versionadas** (v1.0.0 → v1.0.2). En **SereniFlu** implementé un motor de
> mapeo emocional con **94% de exactitud, validada contra un set de casos
> de prueba**.
>
> Mi enfoque va más allá del código: integro **DevOps** en el desarrollo
> móvil (Docker, Makefiles, GitHub Actions) y gestiono el ciclo de
> publicación con canal propio de releases. Pruebas con **mocktail,
> bloc_test e integration_test**, más integración sobre instancia local de
> Supabase.
>
> **Guía técnica abierta de Clean Architecture con Flutter y Supabase**, con
> 25 repositorios públicos de código propio.
>
> Stack: Flutter, Dart, Clean Architecture, FPdart, BLoC/Cubit, GetIt,
> GoRouter, Supabase, PostgreSQL (RLS), Next.js, TypeScript, Tailwind CSS.
> UTC-4 · disponible para solapamiento con EST/PST.

### Texto propuesto — INGLÉS

> Flutter Engineer with **2+ years in Flutter and 3+ years in software
> development**. I started in web frontend (React, Next.js, TypeScript) and
> specialised in Dart and Flutter, building applications with **Clean
> Architecture** and **Functional Programming (FPdart)**.
>
> At IDUCDEV I design and ship complete products end to end. **Rifáme**
> (raffle management) is in **public beta** with **100+ real
> participants**, 3 active raffles and a track record of **5 versioned
> releases** (v1.0.0 → v1.0.2). In **SereniFlu** I built an emotional
> mapping engine with **94% accuracy, validated against a test case set**.
>
> My approach goes beyond code: I bring **DevOps** into mobile development
> (Docker, Makefiles, GitHub Actions) and manage the release cycle with my
> own distribution channel. Tests with **mocktail, bloc_test and
> integration_test**, plus integration against a local Supabase instance.
>
> **Open technical guide to Clean Architecture with Flutter and Supabase**,
> across 25 public repositories of my own code.
>
> Stack: Flutter, Dart, Clean Architecture, FPdart, BLoC/Cubit, GetIt,
> GoRouter, Supabase, PostgreSQL (RLS), Next.js, TypeScript, Tailwind CSS.
> UTC-4 · available for EST/PST overlap.

### Notas de aplicación
- **Longitud:** LinkedIn corta el About a ~3 líneas en el feed. El primer
  bloque (2+ años + Clean Architecture) es el que se ve sin expandir.
- **Emoji:** el perfil anterior usaba emojis como separadores. El texto
  nuevo no los usa; funcionan mejor con hashtags que con emoji en el
  bloque de texto.
- **Elegir un idioma, no ambos.** LinkedIn tiene un solo campo About: usar
  español si el objetivo es LATAM, inglés si es US/EU/global.
- **Enlaces permitidos en el About:** añadir al final
  `iducdev.org` · `github.com/IDUCDEV` · `youtube.com/@iducdev`

---

## 3. EXPERIENCIA

### Diagnóstico del estado anterior
Sonaba a lista de servicios, no a logros. Sin tracción, con una métrica
inmedible y con un proyecto mal atribuido.

### Mobile Engineer / IDUCDEV (jul 2025 - actualidad)

> • Desarrollé y publiqué **Rifáme**, app Flutter de gestión de rifas en
>   **beta pública**: más de **100 participantes reales**, 3 rifas activas
>   y **5 releases versionadas** (v1.0.0 → v1.0.2) con canal de
>   distribución propio.
> • Implementé reserva temporal de números con expiración automática y
>   liberación, más contador de ventas en tiempo real vía Supabase Realtime.
> • Diseñé una arquitectura limpia modular que permite **intercambiar de
>   backend en tiempo de ejecución por configuración** (Supabase ↔ REST API).
> • Desarrollé el **motor de mapeo emocional de SereniFlu** con **94% de
>   exactitud validada contra un set de casos de prueba**.
> • Pruebas unitarias y de widget con **mocktail** y **bloc_test**, más
>   pruebas de integración sobre instancia local de Supabase.
> • Construí una suite de herramientas con **Makefiles y Docker** que redujo
>   el tiempo de setup de entornos de desarrollo.
> • Integré autenticación de Supabase, **Row Level Security** y
>   sincronización en tiempo real sobre PostgreSQL.

**Estado real que este bloque debe reflejar:** ninguna app en Google Play
ni App Store todavía. No escribir "publicada en las stores" (regla R2).

### Frontend Developer / Ayuntamiento de Buchivacoa (feb 2025 - jun 2025)

> • Desarrollé **8 pantallas de interfaz** para el sitio institucional con
>   noticias, formularios de contacto y diseño responsive.
> • Implementé **Server-Side Rendering en Next.js** en el sitio
>   institucional, con una mejora del tiempo de carga frente a la versión
>   anterior.
> • Establecí una **guía de estilo y buenas prácticas de frontend,
>   documentada y adoptada por el equipo**.

### Frontend & Mobile Developer / No Country (ene 2023 - ene 2025)

> • Contribuí en **7+ soluciones multiplataforma** con React, TypeScript y
>   Flutter, en un equipo de trabajo ágil.
> • Reduje los tiempos de respuesta de API mediante caching, code-splitting
>   y optimización de payloads.
> • Trabajé en la **accesibilidad (Lighthouse)** de los proyectos del
>   cliente.

> **Pendiente (D-11):** el contexto de equipo de No Country sigue poco
> detallado. "Simulaciones de desarrollo ágil" es una cita de un rol
> académico: si fue así, decirlo claro; si no, sustituir por el
> contexto real (tamaño de equipo, metodología, rol).

---

## 4. KEYWORDS ESTRATÉGICAS

### Prioridades

| Keyword | Prioridad | Dónde incluirla |
|---------|-----------|-----------------|
| Flutter | Alta | Titular, About, Skills |
| Dart | Alta | Titular, About, Skills |
| Clean Architecture | Alta | Titular, experiencia |
| Flutter Engineer | Alta | Titular |
| Remote / Remoto | Alta | About, ubicación |
| FPdart | Alta | Titular, About, Skills |
| BLoC / Cubit | Media-alta | Skills, experiencia |
| Supabase | Media-alta | Titular, About, Skills |
| mocktail · bloc_test · integration_test | Media-alta | About, experiencia, Skills |
| Clean Architecture Testing / Unit Testing | Media | Skills, experiencia |
| Docker · Makefile | Media | About, Skills |
| GitHub Actions · CI/CD | Media | About, Skills |
| PostgreSQL · Row Level Security | Media | Skills |
| GitHub Releases | Media | experiencia (prueba release engineering) |
| REST APIs · WebSockets | Media | Skills, experiencia |
| Next.js · TypeScript · Tailwind CSS | Media | Skills (perfil fullstack) |
| SOLID · GetIt · GoRouter | Baja-media | Skills |
| RxDart · Provider | Baja | Skills |
| Dokploy · Linux · Bash | Baja | Skills (perfil DevOps) |

### Keywords deliberadamente ausentes

`Riverpod`, `Serverpod`, notificaciones push, funcionalidad offline y
autenticación con Google/Apple **no** se declaran. Están anunciados en
`iducdev.org` pero el usuario no los ha confirmado (D-06, D-07 del base).
No añadirlas a Skills de LinkedIn: un recruiter que pregunte por
Riverpod y no exista es peor que no tener la keyword.

### Gestión de Skills en LinkedIn

LinkedIn permite **50 skills**, muestra 10 por defecto y ordena por
número de endorsements. Estrategia:

1. **Endosar las 10 prioritarias** con perfil 1 y 3 de referencia (genuin,
   nokah, noRk, noMassimo).
2. **Añadir el resto** como skills propias sin endorsement.
3. No añadir skills que no aparezcan como `[M]` en el base.

Lista completa a cargar (las 23 originales + las nuevas marcadas):
Flutter · Dart · Clean Architecture · FPdart · BLoC · Cubit · mocktail ·
bloc_test · Integration Testing · Unit Testing · Widget Testing ·
Supabase · PostgreSQL · Row Level Security · Docker · Docker Compose ·
GitHub Actions · CI/CD · Makefile · Bash · Linux · Dokploy · Git ·
GitHub Flow · REST APIs · WebSockets · Functional Programming · RxDart ·
Provider · GetIt · GoRouter · DevOps · SOLID · Next.js · TypeScript ·
React.js · Tailwind CSS · Figma

*(Son 38; LinkedIn muestra 10, así que el orden de carga importa.)*

---

## 5. PLAN DE CONTENIDO

> La versión anterior cubría junio–julio 2026 y caducó. Re-planeado para
> **septiembre–octubre 2026**, con material que ahora existe y antes no.

### Objetivo
Posicionarte como referente técnico en Flutter + Clean Architecture +
FPdart, y dar visibilidad a los repositorios y productos públicos, que es
donde hoy está tu mejor evidencia.

### Semana 1 — Arquitectura (la base del posicionamiento)
| Día | Tipo | Tema |
|-----|------|------|
| Lun | Post técnico | "Por qué uso FPdart + Clean Architecture en todos mis proyectos Flutter" |
| Mié | Carousel | "5 señales de que tu arquitectura Flutter necesita refactor" |
| Vie | Post | "Cómo desacoplar el backend de una app Flutter con interfaces" |

### Semana 2 — Producto y releases (tu evidencia más fuerte)
| Día | Tipo | Tema |
|-----|------|------|
| Lun | Post | "Cómo llevé Rifáme de 0 a beta pública: usuarios, releases y errores" |
| Mié | Imagen | Captura de la pantalla de rifas + las 5 etiquetas de release |
| Vie | Post | "Publicar sin Play Store: releases versionadas en GitHub" |

### Semana 3 — Testing (el gap que acabas de cerrar)
| Día | Tipo | Tema |
|-----|------|------|
| Lun | Post | "Probar un BLoC sin headache de inyección: mocktail + bloc_test en 4 casos" |
| Mié | Post | "Integration tests contra una instancia local de Supabase" |
| Vie | Post | "Clean Architecture y testing: dónde poner cada tipo de prueba" |

### Semana 4 — Web, infraestructura y comunidad
| Día | Tipo | Tema |
|-----|------|------|
| Lun | Post | "De Frontend Web a Mobile Engineer: mi transición a Flutter" |
| Mié | Post | "Docker + Makefiles para Flutter: menos setup, más entrega" |
| Vie | Post | "Cómo escribo la documentación técnica que luego aplico en el código" |

### Formato
- **Hashtags:** #Flutter #Dart #CleanArchitecture #FPdart #BLoC #MobileDev
- **Frecuencia:** 3 posts/semana (lun, mié, vie)
- **Horario:** 8–10am EST, cuando la audiencia US está activa
- **Cada post debe enlazar a** rifame.org, github.com/IDUCDEV o
  iducdev.org: el perfil pierde valor si el contenido no lleva a un
  producto concreto.

---

## 6. CHECKLIST DE PERFIL

### Identidad y contacto
- [ ] Verificar que el email de contacto sea el **personal**
      (el portafolio publica el freelance)
- [ ] Añadir **YouTube** (youtube.com/@iducdev) en la sección Contacto
- [ ] Añadir **GitHub** y **Portafolio** si no están
- [ ] TikTok: mantener sólo si el objetivo incluye clientes. En una
      postulación a empleo puede restar

### Foto de perfil
- [ ] Fondo neutro o liso
- [ ] Rostro ocupa ~60% del encuadre
- [ ] Luz natural frontal
- [ ] Ropa de casual inteligente

### Banner
- [ ] Personalizado, no el default de LinkedIn
- [ ] Contenido sugerido: `Isaac Urdaneta` + `Flutter Engineer` +
      `Clean Architecture · FPdart · Docker`
- [ ] Herramienta: Canva (plantilla 1584x396px)

### Secciones
- [ ] **Destacados (Featured):** repo de la guía de Clean Architecture,
      Rifáme, portafolio, CV actualizado
- [ ] **Idiomas:** Español nativo / Inglés B1
- [ ] **Licencias y certificaciones:** sólo si existen certificados
      verificables
- [ ] **Servicios:** activar sólo si el objetivo mezcla clientes
- [ ] **#OpenToWork:** activo (ya lo está ✅)

### Reputación
- [ ] Pedir recomendación a colegas de **No Country** (2 años de
      antigüedad ayuda por peso de voz)
- [ ] Pedir recomendación a **clientes de IDUCDEV**
- [ ] Tono: arquitectura, calidad de código, profesionalismo. Evitar
      "soy el mejor" y mencionar resultados concretos
- [ ] Pedir 2-3 reviews de GitHub en los repos Dart activos

---

## 7. ACCIONES PRIORIZADAS

| # | Acción | Tiempo | Impacto |
|---|--------|--------|---------|
| 1 | Aplicar titular opción 1 | 2 min | Alto |
| 2 | Pegar el About nuevo (ES o EN) | 15 min | Alto |
| 3 | Actualizar IDUCDEV con los 7 bullets de la sección 3 | 25 min | Alto |
| 4 | Corregir Buchivacoa: **quitar el 25% de mantenibilidad** | 5 min | Alto |
| 5 | Corregir No Country: **quitar los porcentajes sin método** (35% API, Lighthouse 98) | 5 min | Medio |
| 6 | Cargar las 10 skills prioritarias y endosarlas | 15 min | Medio |
| 7 | Enlazar YouTube, GitHub y portafolio en Contacto | 5 min | Medio |
| 8 | Banner personalizado en Canva | 20 min | Medio |
| 9 | Pedir 2 recomendaciones | 15 min | Medio |
| 10 | Publicar 3 posts/semana durante 4 semanas | 3-4 h/semana | Medio (largo plazo) |
| 11 | Arreglar el PDF del CV (ver O-07 del base: falta `footnote.sty`) | 15 min | Medio |

### Qué NO hacer
- [ ] No escribir "publicada en Google Play" ni "en App Store" (regla R2)
- [ ] No usar "Experto" en ninguna skill ni "Mobile Architect" (regla R3)
- [ ] No declarar Riverpod, Serverpod, push, offline ni auth con
      Google/Apple hasta confirmarlos
- [ ] No usar cifras sin método: los porcentajes de setup de entornos, SSR
      y tiempos de API, y el score de Lighthouse, **no aparecen en los
      bloques de arriba** hasta que se defina cómo se midieron (D-04,
      D-14). Si un recruiter los pide, responder con el método, no con el
      número a secas

---

*Documento derivado de `recursos/cv/base-isaac-urdaneta.md` (banco de
hechos). Si un dato discrepa, el base manda. Regenerado 2026-09-26 con las
respuestas del usuario sobre SereniFlu, Buchivacoa, mocktail/bloc_test y
la guía de estilo.*
