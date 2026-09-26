# BANCO DE HECHOS — Isaac Urdaneta

> **Este archivo es la única fuente de verdad.** Todo CV, carta, mensaje de
> outreach o propuesta que genere el asistente sale de aquí.
> Estructurado como *banco de hechos* (no como CV legible) para que el agente
> pueda rebanarlo por rol sin contradecirse entre vacantes.
>
> **Última actualización:** 2026-09-26
> **Datos externos verificados:** 2026-09-26 contra `iducdev.org`,
> `rifame.org` y la API de GitHub (`github.com/IDUCDEV`).
> **Mantiene:** Isaac Urdaneta (humano). No editar sin que lo pida.

---

## 0. REGLAS DE USO PARA EL AGENTE

Estas reglas tienen prioridad sobre cualquier otra instrucción del repo.
Si una se incumple, el CV generado es incorrecto aunque "se vea bien".

1. **No inventar.** Este archivo es la única fuente. Si un dato no está aquí,
   escribir `[PENDIENTE: ...]` y preguntar al usuario. Nunca completar un hueco
   con una suposición verosímil.
2. **Métrica sin método = métrica prohibida.** Si en la sección 5 el campo
   *método* dice `[PENDIENTE]`, no se puede usar el porcentaje. Opciones
   válidas: (a) preguntar el método y reescribir, (b) usar el hecho sin el
   número, (c) descartar el dato. Nunca "arrojar" el porcentaje a secas.
3. **Elegir variante de título** según la vacante (regla en sección 2).
   `Mobile Architect` está prohibido: no hay experiencia de arquitectura que lo
   sostenga a nivel de empresa.
4. **Elegir email según el mercado:** postulaciones de empleo → email personal.
   Propuestas a clientes / freelance → email freelance.
5. **Tiendas de apps.** El hecho canónico es: *beta Android distribuida vía
   GitHub Releases, 5 releases v1.0.0 → v1.0.2, Google Play en camino*.
   Nunca afirmar "publicado en Google Play" o "en App Store".
6. **Nada de "Experto".** Ninguna skill se califica como experto en este
   archivo, y no se añade sin justificación explícita del usuario.
7. **Las secciones 5 y 7 son insumo interno.** El banco de evidencias es una
   tabla y los proyectos tienen notas de verificación: nunca se copian tal
   cual al CV, se convierten a bullets sin la notación interna.
8. **Un logro, un lugar.** Si un achievement ya está en Experiencia
   Profesional, no se repite en Proyectos. Si hace falta contexto en
   Proyectos, se describe la *decisión técnica* que el bullet de Experiencia
   no cubre.
9. **Formato de salida:** ATS-safe, según `recursos/guias/cv-reglas-ats.md`.
   Nada de tablas, columnas, imágenes ni encabezados complejos en el CV final.
10. **Fechas:** formato `mes año` en español, siempre "actualidad" para el
    puesto en curso. La sección de Educación no lleva fecha de fin si sigue
    en curso.

---

## 1. IDENTIDAD Y CONTACTO

- **Nombre:** Isaac Urdaneta
  - Para orden alfabético inverso en sistemas de ATS: `Urdaneta, Isaac`
- **Rol objetivo principal:** Flutter Engineer
- **Ubicación:** Venezuela · Zona horaria UTC-4
- **Modalidad:** 100% remoto (global). Disponibilidad para solapamiento con
  EST / PST / hora de LATAM.
- **Disponibilidad:** inmediata
- **Email personal (EMPLEO):** urdanetacuarteisaacdavid@gmail.com
- **Email freelance (CLIENTES):** iducdev.inc@gmail.com
- **LinkedIn:** linkedin.com/in/isaac-urdaneta
- **GitHub:** github.com/IDUCDEV
- **Portafolio:** www.iducdev.org
- **YouTube:** youtube.com/@iducdev *(canal de contenido técnico)*
- **TikTok:** tiktok.com/@iducdev *(`[solo variante freelance]`: en una
  postulación a empleo es opcional y puede restar)*

> **Nota:** el portafolio publica únicamente el email freelance. Para
> postulaciones de empleo el primario es el personal.

---

## 2. TÍTULOS APROBADOS

Se usa **uno** según el tipo de vacante. Nunca combinar dos.

| Variante | Título | Cuándo usarla |
|----------|--------|---------------|
| **T1** | `Flutter Engineer \| Clean Architecture & FPdart \| Supabase` | Vacante mobile / Flutter puro. **Por defecto.** |
| **T2** | `Flutter Engineer & DevOps \| Docker, CI/CD \| Supabase` | La vacante pide Docker, CI/CD, deploy, infraestructura o Linux. |
| **T3** | `Frontend & Mobile Engineer \| Flutter, Next.js, TypeScript` | La vacante es web/fullstack con React, Next.js o TypeScript. |
| **T4** | `Desarrollador Freelance de Apps Móviles y Web \| Flutter, Next.js, Supabase` | Sólo para clientes (propuestas, Workana, consultas). |

**Prohibido:** `Mobile Architect`, `Solutions Architect`, `Flutter Expert`,
`Desarrollador Flutter Senior` (salvo que la vacante exija ese nivel y el
agente lo justifique ante el usuario).

---

## 3. PERFIL — BANCO DE AFIRMACIONES

Hechos reutilizables. Combinar en un párrafo de 3-5 líneas según la vacante.
**No son párrafos listos para copiar.**

- **Años de experiencia:** 2+ años en Flutter · 3+ años en desarrollo de
  software. (Los 3+ años inician en enero 2023 en No Country. El grueso del
  trabajo de Flutter es posterior a 2024.)
- **Trayectoria:**enumerate frontend web (React / Next.js / TypeScript) →
  especialización en Dart y Flutter → capa de infraestructura propia
  (Docker, Makefiles, CI/CD) aplicada al desarrollo móvil.
- **Diferenciador 1 — arquitectura:** Clean Architecture con inversión de
  dependencias por interfaces, que permite intercambiar de backend en
  tiempo de ejecución mediante configuración (Supabase ↔ REST API).
- **Diferenciador 2 — FPdart:** Programación Funcional en el móvil
  (Either/Option, fpdart). Es lo que le separa del perfil Flutter medio.
- **Diferenciador 3 — DevOps en el móvil:** no sólo escribe código; contenedoriza
  su entorno, automatiza el pipeline y publica binarios. Verificado con
  releases reales de su app (sección 5, E-05).
- **Diferenciador 4 — producto end-to-end:** diseña, desarrolla, despliega y
  da soporte post-lanzamiento. 25 repositorios públicos de código propio.
- **Contexto de mercado:** trabaja desde Venezuela para clientes y
  Employers globales; accustomed a comunicación asíncrona y a entregar
  sin supervisión directa.

---

## 4. STACK TÉCNICO

`[M]` = hands-on, usado en producción.
`[C]` = conocimiento declarado; usar sólo si la vacante lo pide y sin
atribuirle experiencia verificable.
`[P]` = pendiente de confirmar con el usuario → **no usar** hasta resolver.

### 4.1 Móvil & Arquitectura

| Tecnología | Nivel | Notas |
|------------|-------|-------|
| Flutter | [M] | stack principal desde ~2024 |
| Dart | [M] | — |
| BLoC (Cubit) | [M] | gestión de estado principal |
| Clean Architecture | [M] | capas por feature, DI manual |
| SOLID | [M] | — |
| GetIt | [M] | inyección de dependencias |
| GoRouter | [M] | navegación declarativa |
| RxDart | [M] | streams reactivos |
| Provider | [M] | — |
| Riverpod | [P] | aparece en el portafolio, **no confirmado** |
| Serverpod | [P] | aparece en el portafolio, **no confirmado** |

### 4.2 Testing & Calidad

| Elemento | Nivel | Notas |
|----------|-------|-------|
| Unit / Widget / Integration Testing | [M] | Google `integration_test` |
| Pruebas en dispositivos reales y emuladores | [M] | declarado en portafolio |
| Pruebas de usabilidad | [M] | declarado en portafolio |
| Lighthouse (accesibilidad) | [M] | score 98 — ver E-07 |
| `mocktail` | [M] | mocks de dependencias en tests unitarios |
| `bloc_test` | [M] | tests de estados y transiciones de BLoC/Cubit |

### 4.3 Web & Frontend

| Tecnología | Nivel | Notas |
|------------|-------|-------|
| Next.js | [M] | App Router, SSR, deploy en Vercel |
| React | [M] | — |
| TypeScript | [M] | ~10 repos públicos en TS |
| Tailwind CSS | [M] | — |
| Astro | [M] | landing pages |
| HTML / CSS / JavaScript | [M] | proyectos institucionales |
| Syncfusion Charts · FL Chart | [M] | visualización de datos |
| Figma | [M] | diseño de interfaz y prototipado (no sólo colaboración) |

### 4.4 Backend & Datos

| Tecnología | Nivel | Notas |
|------------|-------|-------|
| Supabase | [M] | Auth, Realtime, Edge Functions, Storage |
| Autenticación email + OAuth (Google, Apple) | [P] | declarado en portafolio, **no confirmado** |
| Row Level Security (RLS) | [M] | declarado en portafolio |
| PostgreSQL | [M] | modelado, migraciones, índices, RLS |
| REST APIs | [M] | DIO / http |
| WebSockets | [M] | multijugador en tiempo real |
| Notificaciones push | [P] | declarado como servicio, **no confirmado** |
| Funcionalidad offline | [P] | declarado como servicio, **no confirmado** |

### 4.5 DevOps & Herramientas

| Tecnología | Nivel | Notas |
|------------|-------|-------|
| Docker / Docker Compose | [M] | desarrollo, producción y orquestación |
| GitHub Actions | [M] | CI/CD |
| Makefile | [M] | build, deploy e infraestructura |
| Git Hooks | [M] | pre-commit checks |
| Dokploy | [M] | PaaS autogestionado, dominio + SSL |
| Linux / SSH / Bash | [M] | administración de servidores |
| Git · GitHub Flow | [M] | — |
| GitHub Releases | [M] | canal de distribución de binarios (E-05) |

---

## 5. BANCO DE EVIDENCIAS

> Tabla interna. **No se copia al CV** (regla 0.7). Sirve para que cada
> afirmación del CV tenga un número defendible en entrevista.
> Toda métrica necesita su método de medición.

| ID | Hecho | Método de medición | Fuente verificable |
|----|-------|--------------------|--------------------|
| E-01 | 2+ años de Flutter, 3+ de software | trayectoria laboral (2023 → hoy) | historial de empleo (sección 6) |
| E-02 | 100+ participantes en Rifáme | contador público del sitio | rifame.org |
| E-03 | 3 rifas activas simultáneas | estado en vivo del sitio | rifame.org |
| E-04 | Reserva temporal de números con expiración y liberación automática | funcionalidad observable | rifame.org (FAQ) |
| E-05 | 5 releases de Android, v1.0.0 → v1.0.2, 03–16 sep 2026 | GitHub Releases | github.com/IDUCDEV/gestion-rifas-releases |
| E-06 | 25 repositorios públicos, **2 forks, 4 stars**, 5 en Dart | suma de `forks_count` y `stargazers_count` por repo vía API de GitHub, 2026-09-26 | github.com/IDUCDEV · ambos forks y las 4 stars están en `clariFi`. **Ojo:** la API de perfil de GitHub no expone `forks_count`; leerlo de ahí da 0 por error. Sumar repo por repo |
| E-07 | Lighthouse accesibilidad 98 | Lighthouse | **método:** [PENDIENTE] — ¿en qué página/proyecto y en qué corrida? |
| E-08 | Motor de mapeo emocional con 94% de exactitud — proyecto **SereniFlu** | validación contra un set de casos de prueba | confirmado por el usuario 2026-09-26 · **cuántos casos:** [PENDIENTE, ver D-13] |
| E-09 | Reducción del tiempo de setup de entornos en 50% | — | **método:** [PENDIENTE] — ¿antes/después de qué tarea? |
| E-10 | SSR mejoró el tiempo de carga en 40% — proyecto **Buchivacoa** (Next.js) | — | proyecto confirmado 2026-09-26 · **método:** [PENDIENTE] — ¿Lighthouse / PageSpeed / tiempo manual? |
| E-11 | Tiempos de respuesta de API reducidos en 35% | — | **método:** [PENDIENTE] — ¿frontend o backend? ¿qué endpoint? |
| E-12 | ~~Mantenibilidad del código +25%~~ | — | **DESCARTADA 2026-09-26.** No es medible. Sustituida por E-17 |
| E-13 | 72 issues abiertas gestionadas en 2 repos Dart | API de GitHub, 2026-09-26 | `clariFi`, `gestion-rifas-app` |
| E-14 | Guía técnica pública de Clean Architecture + Flutter + Supabase | repo activo, push 2026-09-24 | github.com/IDUCDEV/clean_arquitecture_guide_flutter_development_with_supabase |
| E-15 | 8 pantallas críticas, 7+ soluciones multiplataforma | conteo directo | **método:** [PENDIENTE] — unidad de medida imprecisa |
| E-16 | Lighthouse 90+ (performance web) | Lighthouse | iducdev.org — **separar de E-07**, es otra medición |
| E-17 | Guía de estilo y buenas prácticas de frontend, **documentada y adoptada por el equipo** | Confirmado por el usuario 2026-09-26 | sustituye a E-12. **Se redacta sin porcentaje** |

---

## 6. EXPERIENCIA PROFESIONAL

### Ingeniero Móvil Freelance · IDUCDEV
**Remoto · julio 2025 - actualidad**

- Desarrollé y publiqué **Rifáme**, app Flutter de gestión de rifas
  desplegada en producción con **más de 100 participantes** y **3 rifas
  activas** (E-02, E-03); opera con un canal público de distribución beta
  para Android y un historial de **5 releases versionadas v1.0.0 → v1.0.2**
  entre el 3 y el 16 de septiembre de 2026 (E-05).
- Diseñé una arquitectura limpia modular que desacopla el dominio de la
  infraestructura mediante interfaces, permitiendo **intercambiar de backend
  en tiempo de ejecución por configuración** (Supabase ↔ REST API).
- Implementé **reserva temporal de números con expiración automática y
  liberación** al no confirmarse el pago, con contador de ventas en vivo
  (E-04).
- Desarrollé el **motor de mapeo emocional de SereniFlu**, con **94% de
  exactitud validada contra un set de casos de prueba** (E-08), análisis de
  tendencias longitudinales y visualización de datos.
- Construí una suite de herramientas con **Makefiles y Docker** que redujo el
  tiempo de configuración de entornos de desarrollo (E-09 — *el porcentaje
  exacto espera el método de medición, D-04*).
- Llevé **3 aplicaciones Flutter y 3 web-apps a producción**; cada una con
  URL pública. Ninguna todavía en Google Play ni App Store.
- Cubro la lógica de negocio con **pruebas unitarias y de widget
  (`mocktail`, `bloc_test`)** y **pruebas de integración sobre una instancia
  local de Supabase**.
- Integré autenticación de Supabase, **sincronización en tiempo real
  (Realtime)** y **Row Level Security** sobre PostgreSQL.

### Desarrollador Frontend · Ayuntamiento de Buchivacoa
**Venezuela · febrero 2025 - junio 2025**

- Implementé **Server-Side Rendering en Next.js** en el sitio institucional,
  con una mejora del tiempo de carga medida frente a la versión anterior
  (E-10 — *el porcentaje exacto espera el método de medición, D-04*).
- Desarrollé **8 pantallas de interfaz** para ese sitio: noticias,
  formularios de contacto y diseño responsive.
- Establecí una **guía de estilo y buenas prácticas de frontend,
  documentada y adoptada por el equipo** (E-17).

### Desarrollador Frontend y Móvil · No Country
**Remoto · enero 2023 - enero 2025**

- Contribuí en **7+ soluciones multiplataforma** con React, TypeScript y
  Flutter.
- Trabajé en la **accesibilidad (Lighthouse)** de los proyectos del cliente
  (E-07 — *atributo y método pendientes de confirmar, D-14*).
- Reduje los tiempos de respuesta de API mediante caching, code-splitting
  y optimización de payloads (E-11 — *el porcentaje exacto espera el método
  de medición, D-04*).

---

## 7. PROYECTOS DESTACADOS

> Máximo 5 entradas. **Nunca repetir un bullet de la sección 6**: aquí se
> describe la decisión técnica o el resultado, no la misma acción.
> `[P]` = pendiente de confirmar. **No incluir repos de landing pages
> salvo que la vacante sea web/marketing** (hay 9 repos de ese tipo y
> diluirían la señal Flutter).

### Rifáme · https://rifame.org
*Plataforma de gestión de rifas comunitarias con sorteo verificable.*
- **Stack:** Flutter (Android), Next.js (web), Supabase, PostgreSQL.
- **Resultado:** producto en producción con 100+ participantes reales y
  3 rifas activas; 5 releases versionadas en 2 semanas.
- **Decisión técnica:** los pagos se coordinan **fuera de la app** (pago
  móvil, Zelle, Binance, efectivo) y la app gestiona estados de ticket;
  el sorteo se resuelve con resultado público y auditable.
- **Estado:** beta Android distribuida vía GitHub Releases. Google Play
  en camino.

### SereniFlu · https://sereniflu.netlify.app
*Bienestar emocional: check-in, sesiones guiadas y seguimiento de progreso.*
- **Stack:** Flutter, Next.js, FPdart, Supabase, PostgreSQL, Clean
  Architecture. *Confirmado 2026-09-26: el error estaba en la tarjeta del
  portafolio, que lo listaba como app web.*
- **Resultado:** motor de mapeo emocional con **94% de exactitud validada
  contra un set de casos de prueba** (E-08) y check-in emocional en menos
  de 30 segundos.
- **Decisión técnica:** el mapeo se isolate en el dominio con FPdart
  (Either/Option), sin depender de la capa de datos — gracias a la
  inversión de dependencias, el mismo dominio sirve tanto a la app Flutter
  como al sitio web.

### Temporus · https://www.temporus.site
*Time-tracking para redes sociales: Pomodoro y hábitos.*
- **Stack:** Flutter, Next.js, Supabase.
- **Resultado:** sincronización multi-dispositivo con latencia mínima.
- **Nota:** mantener fuera de la sección si la vacante es mobile pura; es
  un proyecto de 2025 sin actividad reciente en GitHub.

### Juego PPT · https://juegoppt.site
*Piedra, papel o tijera multijugador en tiempo real.*
- **Stack:** React, TypeScript, WebSockets.
- **Resultado:** salas multijugador con sistema de apuestas y ranking.
- **Valor para Flutter:** evidencia de diseño de estado concurrente y
  tiempo real; es el mejor argumento de transferencia si la vacante
  exige "lógica de juego" o "concurrencia".

### VisDown · https://visdown.netlify.app
*Descargador de videos de múltiples plataformas.*
- **Stack:** Next.js, TypeScript, Tailwind CSS. App móvil en Dart
  (`visdown_mobile_app`).
- **Resultado:** interfaz rápida y responsive; scraping multi-origen.

### Guía técnica — Clean Architecture + Flutter + Supabase
*Documentación pública de arquitectura (E-14).*
- **Repositorio:** `github.com/IDUCDEV/clean_arquitecture_guide_flutter_development_with_supabase`
- **Valor:** technical writing en un stack que la mayoría de devs sólo
  consume. Es la prueba más directa de dominio de Clean Architecture, y
  compensa la ausencia de stars.

---

## 8. EDUCACIÓN · IDIOMAS · CERTIFICACIONES

### Educación

**Ingeniería de Sistemas** — Universidad Nacional Abierta de Venezuela
`[PENDIENTE: año estimado de graduación / semestres cursados]`
enero 2023 - actualidad (en curso)

### Idiomas

- **Español:** nativo
- **Inglés:** B1 · `[PENDIENTE: ¿certificado? ¿fecha? ¿examen?]` — studying
  toward B2/C1. **Nota:** muchas vacantes remotas LATAM filtran en B2; si
  hay certificado o examen próximo, es la palanca más rentable del CV.

### Certificaciones

`[PENDIENTE: ¿tiene alguna? Flutter, Dart, Supabase, Docker, Scrum.]`
Si no hay ninguna, **omitir la sección completa**. No crear entradas de
cursos de Udemy completados sin certificado verificable.

---

## 9. CHECKLIST PENDIENTES

Ordenado por impacto en la candidatura. Cada punto es un dato que falta y
que hoy impide generar un CV más fuerte.

### Resueltos

| # | Pendiente | Resolución (2026-09-26) |
|---|-----------|--------------------------|
| ~~D-01~~ | Librerías de testing | **`mocktail` y `bloc_test`** — ya `[M]` en 4.2 |
| ~~D-02~~ | Proyecto del motor del 94% | **SereniFlu** — el error estaba en el portafolio |
| ~~D-03~~ | Stack del proyecto de Buchivacoa | **Next.js**, mismo sitio del +40% SSR — el error estaba en el portafolio |
| ~~D-05~~ | Sustituto de "mantenibilidad +25%" | **Guía de estilo documentada y adoptada por el equipo** (E-17) |
| ~~D-06~~ | Riverpod y Serverpod | **NO CONFIRMADOS.** Siguen `[P]`, fuera de todo documento |
| ~~D-07~~ | Push, offline y auth Google/Apple | **NO CONFIRMADOS.** Siguen `[P]`, fuera de todo documento |

### Abiertos

| # | Pendiente | Por qué importa | Bloquea |
|---|-----------|-----------------|---------|
| **D-04** | Métodos de medición de E-07 (98 Lighthouse), E-09 (50% setup), E-10 (40% SSR) y E-11 (35% API) | sin método, el porcentaje no es utilizable (regla 0.2) | 4 métricas |
| **D-08** | Año estimado de graduación | filtro de ATS | sección 8 |
| **D-09** | ¿Certificado de inglés? | filtro duro en muchas vacantes | sección 8 |
| **D-10** | ¿Certificaciones técnicas? | si hay, suben el match de keywords | sección 8 |
| **D-11** | Contexto real de No Country: "simulaciones ágiles", roles, tamaño del equipo | el CV no describe equipo ni metodología | sección 6 |
| **D-12** | Modelo de ingresos de Rifáme: cuántos organizadores y volumen de transacciones | da escala de negocio, no sólo usuarios | sección 7 |
| **D-13** | ¿Cuántos casos tenía el set de validación del 94%? | de una línea, y convierte una afirmación en un dato muestral defendible | E-08 |
| **D-14** | ¿En qué proyecto y en qué corrida el score 98 de Lighthouse? | E-07 sigue sin proyecto atribuible | E-07 |

### Objetivos de impacto (no bloqueantes, pero valen puntos)

- **O-01:** publicar Rifáme en Google Play. Es la brecha que más cuesta en
  una postulación mobile y ya está a un paso (beta pública funcionando).
- **O-02:** stars/forks siguen siendo una señal débil: 4 stars y 2 forks en
  todo el perfil, los dos en `clariFi` (ver E-06, ya corregido). Por eso la
  métrica de GitHub **no va en el About de LinkedIn**: 25 repositorios
  públicos sí es dato, pero la cifra de forks/stars se lee como relleno.
  Citar el repo de la guía técnica (E-14) sí suma.
- **O-03:** ~~corregir `linkedin.md`~~ — **hecho 2026-09-26**, regenerado
  desde este base.
- **O-04:** el portafolio afirma "+5 años de experiencia" frente a los 3+
  defendibles aquí. **Alinear** (ver O-06).
- **O-05:** generar los canónicos ES/EN que `recursos/INDICE.md` lista y que
  no existen todavía en `recursos/cv/`.
- **O-06 — el portafolio es ahora la fuente desactualizada, no este archivo.**
  Tras las respuestas del 2026-09-26 hay que corregir `iducdev.org`:
  - Tarjeta de **SereniFlu**: dice "aplicación web" con stack
    `Next.js, Tailwind, TypeScript` → es **Flutter + FPdart + Supabase**.
  - Tarjeta de **Buchivacoa**: dice `HTML, CSS, JavaScript` → es
    **Next.js + TypeScript**.
  - Página de **Servicios**: retirar **Serverpod**, **Riverpod**,
    **notificaciones push**, **funcionalidad offline** y **auth con
    Google/Apple** hasta que se confirmen como `[M]` (D-06, D-07).
  - Hero: "+5 años" → **3+ años**.
  - Filtro de proyectos: "Apps Móviles 0" → Rifáme es una app móvil en
    beta con URL de descarga, no sólo web.
- **O-07:** `pandoc` no genera PDF en esta máquina (LaTeX sin
  `footnote.sty`). El flujo de `cv-apply` no puede entregar PDF hasta
  instalar `texlive-latex-recommended` o cambiar a `weasyprint`.
