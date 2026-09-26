# PROMPT PARA GENERAR CVs OPTIMIZADOS ATS

## INPUT RECIBIDO

- **CV Base (banco de hechos):** `recursos/cv/base-isaac-urdaneta.md`
- **Vacante:** [Descripción completa del puesto/vacante]

> **El CV base ya no es un CV: es un banco de hechos** con reglas de uso
> propias (sección 0), títulos approved (sección 2), stack marcado por nivel
> de dominio (sección 4), banco de evidencias con métodos de medición
> (sección 5) y checklist de pendientes (sección 9). Leer la sección 0
> **antes** de generar nada: sus reglas prevalecen sobre este documento.

---

## REGLAS DE INTEGRIDAD (prioridad máxima)

> Un CV que exagera el perfil consigue una entrevista y la pierde en el
> technical round. Estas reglas son de cumplimiento obligatorio.

### R1. Una métrica sin método no se usa
Antes de escribir un porcentaje, mira su fila en el **banco de evidencias
(sección 5)**. Si el campo *método* dice `[PENDIENTE]`, tienes tres salidas
legítimas: preguntar el método al usuario, usar el hecho **sin** el número,
o descartar el dato. Nunca "arrojar" el porcentaje a la espera de que
nadie pregunte.

**Aplicado a día de hoy — cuatro métricas en cuarentena.** E-07 (98
Lighthouse), E-09 (50% setup), E-10 (40% SSR) y E-11 (35% API) tienen
método `[PENDIENTE]`. Sus hechos sí se usan; **sus porcentajes no**:

| Hecho permitido | Por qué se permite |
|---|---|
| "redujo el tiempo de setup de entornos de desarrollo" | el hecho es verificable, la cifra no |
| "mejora del tiempo de carga frente a la versión anterior" (Buchivacoa) | proyecto confirmado, método pendiente |
| "reduje los tiempos de respuesta de API mediante caching y code-splitting" | describe la intervención, no un número sin fuente |
| "trabajé en la accesibilidad (Lighthouse) de los proyectos del cliente" | proyecto aún sin atribuir (D-14) |

Si una vacante pide específicamente una de estas métricas, la respuesta
correcta es **preguntar el método al usuario en el momento**, no escribirlo
y esperar. La cifra sólo vuelve al CV cuando hay un nombre de herramienta o
un procedimiento detrás.

### R2. Nada de tiendas de apps sin evidencia
Hecho canónico: **beta Android distribuida vía GitHub Releases, 5 releases
v1.0.0 → v1.0.2, Google Play en camino.** Se puede escribir "publicada en
beta", "distribuida por canal propio", "100+ usuarios reales". Prohibido:
"publicada en Google Play", "en App Store", "en producción en tiendas".
Si la vacante exige publicación en stores, decirlo con franqueza y usar el
resto de argumentos (100+ usuarios, releases versionadas, ciclo completo
de build) en lugar de inventar la store.

### R3. Prohibido "Experto" y "Mobile Architect"
Ninguna skill se califica como experto en el banco de hechos, y no se
califica en la salida. `Mobile Architect` y `Solutions Architect` están
prohibidos como título: no hay experiencia de arquitectura a ese nivel que
los sostenga. Para seniority, usar la escala de la vacante y ajustar la
redacción a lo defendible en entrevista.

### R4. Un logro, un lugar
Si un achievement ya aparece como bullet en Experiencia, no se repite en
Proyectos. En Proyectos se describe la **decisión técnica** o el **resultado**
que el bullet de Experiencia no cubre. Repetir el mismo logro en dos
secciones es la señal más rápida de un CV generado sin criterio.

### R5. Las palabras clave sin confirmar no se usan
El stack viene marcado `[M]` hands-on, `[C]` conocimiento, `[P]` pendiente.
**`[P]` no se escribe en el CV bajo ninguna circunstancia.** Se resuelve
antes con el usuario (checklist de la sección 9 del base) o se omite.
Esto aplica especialmente a librerías de testing, Riverpod, Serverpod,
push notifications y modo offline.

### R6. Coherencia entre canales
Si un dato aparece en el CV, debe ser coherente con el portafolio
(`iducdev.org`), GitHub y LinkedIn. Al detectar contradicciones
—p. ej. el portafolio afirma "+5 años" y el base 3+ defendibles—, reportar
al usuario en lugar de elegir silenciosamente una versión.

---

## INSTRUCCIONES DE GENERACIÓN

### 0. TÍTULO Y VARIANTES (antes de redactar)

Elegir **una** de las cuatro variantes de la sección 2 del banco de hechos:

| Variante | Cuándo |
|----------|--------|
| **T1** Flutter Engineer | por defecto; vacante mobile / Flutter puro |
| **T2** Flutter Engineer & DevOps | la vacante pide Docker, CI/CD, deploy, infra o Linux |
| **T3** Frontend & Mobile Engineer | la vacante es web/fullstack: React, Next.js, TypeScript |
| **T4** Desarrollador Freelance | sólo clientes (propuestas, Workana) |

También elegir el email: **empleo** → email personal; **clientes** →
email freelance.

### 1. ANÁLISIS DE LA VACANTE

Extrae y categoriza:

**Requisitos Técnicos:**
- Frameworks y lenguajes mencionados
- Herramientas y tecnologías requeridas
- Infraestructura y DevOps (Docker, CI/CD, despliegue, orquestación)
- Experiencia mínima (años)
- Certificaciones necesarias

**Requisitos Funcionales:**
- Responsabilidades clave (verbos de acción)
- Modalidad de trabajo (remoto/híbrido/presencial)
- Ubicación
- Idiomas

**Palabras Clave ATS:**
Lista todas las palabras técnicas y funcionales que aparezcan en la vacante.

---

### 2. MAPEO CV BASE vs VACANTE

Para cada requisito de la vacante:
- ✓ Coincide directamente → mantener
- ⚠ Coincide parcialmente → adaptar descripción
- ✗ No mentioned → agregar si es relevante o incluir como "conocimiento"
- ✗ No aplica → omitir

**Mapeo específico de DevOps/Infraestructura:**
- Si la vacante es **solo mobile** → reducir DevOps a lo esencial (Docker, Makefile), omitir Dokploy/SSH
- Si la vacante es **mobile + DevOps/infra** → mantener y alinear descripciones
- Si la vacante es **solo infra/DevOps** → pivotar: infraestructura como skill principal, mobile como background complementario

---

### 3. REESCRITURA OPTIMIZADA

**Resumen Profesional:**
- Reescribir para enfatizar requisitos de la vacante
- Incluir keywords principales en primeras 2 líneas
- Mencionar años de experiencia específicos
- Incluir modalidad de trabajo

**Habilidades Técnicas:**
- Partir de la sección 4 del banco de hechos y reordenar: primero lo que
  pide la vacante
- **Incluir sólo `[M]` y, si es imprescindible para el match, `[C]`.
  Nunca `[P]`** (regla R5)
- Usar formato: "Tecnología - Uso/Aplicación"
- Para roles mixtos (mobile + infra): dividir en subcategorías claras
  (Core, Infraestructura, QA)
- Para roles puramente mobile: fusionar DevOps/Infra en una línea
  "DevOps & QA"
- **Keyword testing:** `mocktail`, `bloc_test` e `integration_test` están
  `[M]` en la sección 4.2 del base, así que son **obligatorias** en toda
  vacante Flutter que pida testing. Es el bloque que más filtra y el que
  antes faltaba por completo
- **Keyword release/build**: si la vacante pide publicación en stores,
  CI/CD o release management, usar los hechos E-05 (5 releases
  versionadas, canal público) y el bloque DevOps. No sustituirlo por
  "publicado en Play Store" (regla R2)

**Experiencia Profesional:**
- Para cada puesto: reescribir bullet points
- Resaltar achievements alineados con vacante
- Incluir métricas **sólo si su método no es `[PENDIENTE]`** (regla R1)
- Usar verbos de acción (desarrollé, implementé, lideré, optimicé, etc.)
- Distinguir achievement propio de contribución de equipo: "contribuí" o
  "formé parte" no es "lideré"

**Proyectos:**
- Seleccionar los más relevantes a la vacante
- Reescribir para enfatizar habilidades requeridas
- **Máximo 5 entradas.** Descartar los repos de landing pages/marketing
  salvo que la vacante sea web o de generación de leads: son 9 de los 25
  repos públicos y diluyen la señal Flutter
- Incluir la URL pública y el estado real (producción / beta / en curso)
- No repetir ningún bullet de Experiencia (regla R4)

---

### 4. OPTIMIZACIÓN ATS

**Keywords:**
- Incluir TODAS las palabras clave de la vacante
- Density: 3-5% del contenido total
- Evitar sinónimos que ATS no reconozca

**Formato ATS-Safe:**
- ❌ No headers complejos
- ❌ No tablas
- ❌ No columnas
- ❌ No imágenes
- ✓ Headers simples: ## or ===
- ✓ Listas con guiones o bullets simples
- ✓ Texto plano, sin footnotes

**Estructura Recomendada:**

```
# [NOMBRE] - [TÍTULO/PUESTO]

## Datos de Contacto
[Info de contacto en una línea]

## Perfil Profesional
[Párrafo de 3-5 líneas optimizado con keywords]

## Habilidades Técnicas
[Lista categorizada]

## Experiencia Profesional
[Sin fechas detalladas en headers]

## Proyectos Destacados
[Si aplica: máx. 5, con URL y estado real]

## Educación
[Solo lo esencial]

## Idiomas
[Con nivel real; sin inventar nivel ni certificado]
```

> **Eliminado de la plantilla: la sección "Referencias".** Ocupa espacio,
> no filtra nada en procesos LATAM/US y añade una línea de mantenimiento.
> No incluirla.

---

### 5. GENERACIÓN DEL OUTPUT

**Archivo de salida:** `{nombre-base}-{Rol/especialidad}-{empresa}.md`

En markdown limpio, optimizado para parseo ATS.

*Idioma:** Español profesional (o según idioma de vacante)

**Antes de escribir el archivo, verificar contra la lista de integridad:**

- [ ] ¿Usé sólo una variante de título (sección 2 del base)?
- [ ] ¿El email corresponde al mercado (empleo vs clientes)?
- [ ] ¿Alguna métrica sin método resuelto? Si sí, ¿la quité o la
      presenté sin el número?
- [ ] ¿Aparecen sólo skills `[M]`/`[C]`, ninguna `[P]`?
- [ ] ¿Dije "publicado en Play Store" o "App Store"? → corregir (R2)
- [ ] ¿Usé "Experto" o "Mobile Architect"? → corregir (R3)
- [ ] ¿Repetí algún achievement entre Experiencia y Proyectos? → corregir (R4)
- [ ] ¿Algún dato contradice portafolio, GitHub o LinkedIn? → reportar (R6)
- [ ] ¿Dije "Referencias"? → eliminar
- [ ] ¿Declaré librerías de testing sin que estén `[M]`? → avisar al
      usuario del gap, no rellenarlo

---

## EJEMPLOS DE APLICACIÓN

### Ejemplo 1: Mobile (Flutter Senior con stores)

**Input Vacante Stefanini:**
- Desarrollador Flutter Senior
- Remoto
- Clean Architecture, BLoC, APIs REST
- **Publicación en Stores (requisito duro)**

**Output Generado:**
- Título: variante **T1** — "Flutter Engineer | Clean Architecture & FPdart
  | Supabase". No "Flutter Expert" ni "Mobile Architect" (R3)
- Resumen: keywords Flutter, Clean Architecture, BLoC, APIs REST
- Experiencia: aquí se aplica **R2**. No se puede afirmar publicación en
  stores, así que se juega con los hechos equivalentes: "beta pública
  con canal propio de distribución, **5 releases versionadas**
  (v1.0.0 → v1.0.2) en dos semanas y **más de 100 usuarios reales**",
  "Google Play en camino". La brecha de store se dice explícitamente,
  no se disimula
- Testing: `mocktail`, `bloc_test` e `integration_test` entran como
  skill **y** como bullet, porque la vacante casi seguro los filtra
- Pendiente a reportar: D-04 (si la vacante pide métricas de
  rendimiento, sin método no se usa el porcentaje)

### Ejemplo 2: Infraestructura (Platform/DevOps)

**Input Vacante:**
- Platform Engineer / DevOps
- Remoto
- Docker, CI/CD, despliegue de servicios
- Experiencia con servidores Linux

**Output Generado:**
- Título: variante **T2** — "Flutter Engineer & DevOps | Docker, CI/CD |
  Supabase". **No** "Platform Engineer & Mobile Architect" (R3)
- Resumen: Docker, infraestructura autogestionada; mobile como segundo eje
- Skills: DevOps/Infraestructura primero (Docker, Docker Compose, Dokploy,
  GitHub Actions, SSH, Bash, Makefile, Linux, GitHub Releases), luego Core
  mobile
- Experiencia: suite Makefiles/Docker, releases versionadas, gestión de
  servidores
- Proyectos: Rifáme (ciclo completo build → release → despliegue),
  Temporus. **Omitir** landing pages de GitHub

### Ejemplo 3: Web / Fullstack

**Input Vacante:**
- Fullstack Developer (React / Next.js / TypeScript)
- Backend con Supabase o similar

**Output Generado:**
- Título: variante **T3** — "Frontend & Mobile Engineer | Flutter,
  Next.js, TypeScript"
- Resumen: destaca la experiencia web de 3 años (2023 en adelante) y el
  stack de TypeScript; Flutter como ventaja adicional
- Skills: Next.js, React, TypeScript, Tailwind primero; luego Supabase,
  PostgreSQL, Flutter
- Experiencia: Buchivacoa (frontend, Next.js + SSR), No Country
  (multiplataforma)

---

## USO DEL PROMPT

1. Leer `recursos/cv/base-isaac-urdaneta.md` **completo**, empezando por
   la sección 0 (reglas de uso del agente)
2. Elegir variante de título (sección 2 del base) y email según mercado
3. Leer descripción de vacante proporcionada
4. Ejecutar instrucciones 0-5 + reglas R1-R6
5. Pasar la checklist de integridad de la sección 5
6. Guardar output como nuevo archivo markdown
7. Convertir a PDF usando Pandoc:

```bash
pandoc input.md -o output.pdf \
  -V mainfont="sans-serif" \
  -V fontsize=11 \
  -V geometry=margin=1in \
  --standalone
```

> El base tiene tablas y notación interna (`[M]`, `[P]`, IDs E-xx) que
> **nunca** se copian al CV. El PDF sale del markdown generado, no del base.

---

## CRITERIOS DE CALIDAD

### ATS / match

- [ ] Coincidencia de keywords ≥ 80%
- [ ] Años de experiencia reflejados correctamente (2+ Flutter, 3+ software)
- [ ] Modalidad de trabajo especificada (remoto, UTC-4, solapamiento)
- [ ] Sección DevOps/Infraestructura adaptada al tipo de rol (mobile vs mixto vs infra)
- [ ] Formato ATS-safe verificado
- [ ] Archivo genera PDF correctamente

### Integridad (bloqueantes: si falla uno, no se entrega)

- [ ] **R1** Toda métrica usada tiene método conocido, o se presentó sin el número
- [ ] **R2** Ninguna afirmación sobre Google Play / App Store
- [ ] **R3** Sin "Experto" ni "Mobile Architect"
- [ ] **R4** Ningún achievement repetido entre Experiencia y Proyectos
- [ ] **R5** Ninguna skill `[P]` presente en la salida
- [ ] **R6** Sin contradicción con portafolio / GitHub / LinkedIn
- [ ] Sin sección "Referencias"
- [ ] Título = una de las 4 variantes; email = el del mercado

### Señal (calidad, no bloqueante)

- [ ] ¿Lleva **al menos una métrica de tracción** (usuarios, releases,
      estrellas, volumen)? Es lo que separa este CV de un CV genérico
- [ ] ¿Los proyectos incluyen URL pública y estado real?
- [ ] ¿Se reportaron al usuario los `[PENDIENTE]` relevantes para esta
      vacante, para que no se repitan huecos en la siguiente postulación?

---

## PENDIENTES CONOCIDOS DEL BANCO DE HECHOS

Estos huecos limitan lo que el CV puede afirmar. Checklist completo en la
sección 9 de `recursos/cv/base-isaac-urdaneta.md`.

**Resueltos 2026-09-26** (ya no son huecos): librerías de testing
(`mocktail`, `bloc_test` → `[M]`), proyecto del motor del 94% (**SereniFlu**),
stack de Buchivacoa (**Next.js**), sustituto de la métrica de mantenibilidad
(**guía de estilo documentada y adoptada**).

| ID | Hueco | Efecto en el CV |
|----|-------|-----------------|
| D-04 | Métodos de medición de E-07, E-09, E-10 y E-11 | 4 métricas salen **sin el porcentaje** hasta que se defina la herramienta de medición |
| D-08 | Año estimado de graduación | filtro de ATS sin resolver |
| D-09 | Certificado de inglés | filtro duro en muchas vacantes remotas |
| D-10 | Certificaciones técnicas | si existen, suben el match de keywords |
| D-11 | Contexto de equipo en No Country | el CV no describe metodología ni tamaño de equipo |
| D-12 | Modelo de ingresos de Rifáme | falta la escala de negocio, no sólo usuarios |
| D-13 | Tamaño del set de validación del 94% | el dato es defendible, pero no muestral |
| D-14 | Proyecto y corrida del score 98 de Lighthouse | E-07 sin atribución |

### Keywords deliberadamente ausentes

`Riverpod`, `Serverpod`, notificaciones push, funcionalidad offline y
autenticación con Google/Apple están **declarados en `iducdev.org` pero no
confirmados** por el usuario (D-06, D-07). Siguen marcados `[P]` y **no
aparecen en ningún documento generado**, aunque el portafolio los anuncie
como servicio. Si el usuario los confirma, pasan a `[M]` y hay que corregir
el portafolio en el mismo momento (ver O-06 en el base).

> Coste real de esta decisión: son keywords que casi toda vacante Flutter
> lista. No es un defecto del CV, es una decisión de no afirmar lo no
> confirmado. Si el usuario prefiere cubrirlas, el camino es implementarlas,
> no declararlas.
