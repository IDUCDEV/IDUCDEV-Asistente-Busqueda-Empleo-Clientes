# IDUCDEV — Asistente de Búsqueda de Empleo y Clientes

**Este documento ES la guía completa del proyecto.** Si quieres saber algo
del asistente, está aquí: qué hace, cómo se usa, dónde están tus recursos,
dónde quedan los resultados y cómo se restaura.

---

## 1. ¿Qué es esto?

Un asistente personal que hace por ti el proceso tedioso de buscar
**empleo** (vacantes Flutter/Dart remotas LATAM + freelance + mercado
oculto de LinkedIn) y **clientes** (negocios venezolanos y empresas target).
**Y nunca te vuelve a mostrar lo que ya viste** (deduplicación central).

Todo se divide en dos zonas del proyecto:

- **`recursos/`** → lo que el asistente **consulta** (tu CV base, reglas
  ATS, guías). Tú las mantienes.
- **`resultados/`** → lo que el asistente **produce** (listados de vacantes,
  leads, CVs generados, mensajes, informes). Se regeneran solos.

---

## 2. Cómo se usa (para ti, el humano)

No tienes que saber de skills ni de carpetas. Solo habla con el asistente.
Frases que entiende:

| Di esto | Qué hace por ti |
|---------|-----------------|
| **"Haz la ronda de hoy"** | Busca vacantes nuevas (7 fuentes) + proyectos Workana + posts ocultos de LinkedIn + leads de clientes + empresas target. **Omite lo ya visto** y te deja un resumen. |
| **"Solo empleos"** | Solo la parte de búsqueda de trabajo. |
| **"Solo clientes"** | Solo descubrir potenciales clientes. |
| **"¿Qué hay nuevo?"** | Te dice lo pendiente de revisar y las tareas sin volver a buscar. |
| **"¿Qué tengo pendiente?"** | Muestra la bandeja de tareas (seguimientos de contactos y aplicaciones). |
| **"Aplica a {x}"** | Genera CV optimizado ATS + carta + PDF para esa vacante, con el link pegado. |
| **"Contacta a {perfil}"** | Genera el mensaje personalizado para ese reclutador/empresa en LinkedIn. |
| **"Contacta a {cliente}"** | Genera el mensaje de venta personalizado para un lead (WhatsApp/email/LinkedIn) y lo deja **en cola** de envío. |
| **"Envía los pendientes"** | Envía los mensajes en cola **uno por uno**: te muestra cada mensaje, lo validas o lo corregimos, se envía y pasamos al siguiente. Máx 12/día. |
| **"Marca {x} como aplicado"** | Lo registra como hecho y agenda un seguimiento automático. |
| **"Guía"** | Muestra este documento resumido. |

### Ejemplos reales

```
"Haz la ronda de hoy"
"¿Qué hay nuevo?"
"Solo empleos"
"aplica a esta vacante: <pega el texto o link>"
"contacta a https://www.linkedin.com/in/xxx"
"contacta a Clínica CCCT"
"envía los pendientes"
"marca Flutter Developer en GetOnBoard como aplicado"
"¿algún cliente nuevo esta semana?"
"¿qué tengo pendiente?"
```

> El asistente abre el navegador (LinkedIn, leads, empresas) **solo si se lo
> autorizas**. El resto lo hace solo.

---

## 3. Centro de recursos (`recursos/`) — lo que el asistente consulta

Aquí viven tus materiales de entrada. El asistente **lee este índice antes
de cada skill**: `recursos/INDICE.md`.

| Recurso | Ruta | Quién lo actualiza |
|---------|------|--------------------|
| CV base | `recursos/cv/base-isaac-urdaneta.md` | **Tú** (ver abajo) |
| CV canónico Español | `recursos/cv/CV-isaac-urdaneta-ES.md` + `.pdf` | Tú / puntual |
| CV canónico Inglés | `recursos/cv/CV-isaac-urdaneta-EN.md` + `.pdf` | Tú / puntual |
| Reglas ATS | `recursos/guias/cv-reglas-ats.md` | Agente (ajustes) |
| Guía LinkedIn | `recursos/guias/linkedin.md` | Tú / agente a demanda |

### Cómo actualizar tu CV base

1. Edita `recursos/cv/base-isaac-urdaneta.md` con tus datos actualizados
   (contacto, stack, experiencia, proyectos).
2. Git lleva el **versionado**: cada cambio queda historial, así que puedes
   volver atrás si lo necesitas.
3. Pídele al asistente: *"actualicé mi CV base, revisa lo que afecta"* si
   quieres que verifique que los CVs canónicos (ES/EN) sigan alineados.

> No modifiques los archivos base en una sesión normal: son la fuente de
> verdad. Los CVs optimizados por vacante se generan sin tocar el original.

---

## 4. Resultados (`resultados/`) — dónde queda cada cosa

Todo lo que las skills producen cae en una carpeta por skill:

| Skill / Acción | Resultado |
|----------------|-----------|
| Buscador de vacantes (`job-search`) | `resultados/vacantes/{fecha}.md` |
| Freelance (Workana) | `resultados/vacantes-workana/{fecha}.md` |
| Mercado oculto de LinkedIn | `resultados/vacantes-ocultas/{fecha}-hidden.md` |
| CVs optimizados (`cv-apply`) | `resultados/cv/{cv-base}-{rol}-{empresa}.md` + carta + PDF |
| Mensajes de contacto (empleo) | `resultados/mensajes-outreach/{nombre}-{fecha}.md` |
| Mensajes a clientes | `resultados/mensajes-clientes/{nombre}-{fecha}.md` + cola `estado/cola_envios.json` |
| Envío de mensajes a clientes | `enviar-clientes`: email SMTP automático, WhatsApp Web (navegador), LinkedIn semi |
| Empresas target | `resultados/empresas-target/{fecha}-empresas.md` + `leads-db.json` |
| Leads de clientes | `resultados/clientes-potenciales/{fecha}-leads.md` + `leads-db.json` |
| Resumen diario | `resultados/informes/{fecha}-resumen.md` |

Los `resultados/` están ignorados por git: se regeneran en cada ejecución y
no ensucian el repo.

---

## 5. El cerebro (`estado/`) y cómo no se repite nada

| Archivo | Qué es |
|---------|--------|
| `config.py` | Fuente única de rutas (`.iducdev-root`, nunca hardcodear) |
| `historial.json` | Base central "no repitas esto" (dedup) |
| `tareas.json` | Bandeja de entrada (acciones + vencimientos) |
| `rondas.json` | Bitácora de rondas (fases + conteos) |
| `cola_envios.json` | Cola de mensajes a clientes listos para enviar |
| `tracker.py` | Helper del historial (consulta/registro/estado) |
| `orquestador.py` | CLI: `ronda`, `registrar`, `estado`, `marcar`, `tareas`, `informe`, `reset` |

**Cómo funciona el ciclo de estado:** `nuevo → revisado → en_proceso →
aplicado/enviado → respuesta/descartado`. Cuando marcas algo como aplicado o
contactado, el asistente agenda un **seguimiento automático** (D+3 para
contactos y clientes, D+7 para aplicaciones) y te lo recuerda en *"¿qué tengo
pendiente?"*.

**Contactar a un cliente es ahora 2 pasos:** "contacta a {cliente}" deja el
mensaje **en cola**; luego "envía los pendientes" arranca la ronda uno por
uno: te muestra cada mensaje completo, lo validas (ok / modificar /
saltar), se envía (email automatico; WhatsApp Web pide que estes logueado
y autorizacion del navegador; LinkedIn te deja el mensaje pegado para que
tu pulses enviar) y pasamos al siguiente. Te avisa cuando llegas al limite
diario.

---

## 6. Estructura del proyecto

```
├── GUIA.md                       # Este documento (única guía completa)
├── AGENTS.md                     # Reglas para agentes de IA del repo
├── README.md                     # Portada → enlaza a esta guía
├── recursos/                     # CENTRO DE RECURSOS (tú los mantienes)
│   ├── INDICE.md                 # Mapa maestro que el agente consulta
│   ├── cv/                       # Base + CVs canónicos + PDFs
│   └── guias/                    # Reglas ATS, guía LinkedIn
├── resultados/                   # RESULTADOS por skill (se regeneran)
│   ├── vacantes/  vacantes-workana/  vacantes-ocultas/
│   ├── clientes-potenciales/  empresas-target/
│   ├── mensajes-outreach/  mensajes-clientes/  cv/  informes/
├── .opencode/
│   ├── skills/                   # Las 9 skills (proyecto-only)
│   └── command/                  # /ronda /estado /nuevo
├── .opencode/skills/...          # skills
├── docs/SKILLS.md                # Detalle técnico de las skills
└── estado/                       # El cerebro (ver sección 5)
```

---

## 7. Comandos rápidos (opcional, vía CLI)

```bash
python3 estado/orquestador.py estado          # tablero: historial + tareas + vencidos
python3 estado/orquestador.py tareas          # bandeja de entrada
python3 estado/orquestador.py seguimientos    # seguimientos vencidos/próximos
python3 estado/orquestador.py ronda --empleos # fases 1-2 + informe
python3 estado/orquestador.py informe         # regenera el resumen del día
python3 estado/cola_envios.py pendientes      # mensajes a clientes en cola
python3 estado/cola_envios.py enviados-hoy    # cupo usado del día
python3 estado/orquestador.py reset --yes     # ¡CUIDADO! vacía historial/tareas/rondas (reempezar)
```

> `reset` borra la deduplicación central (historial), la bandeja de entrada
> (tareas) y la bitácora (rondas): todo lo ya visto volverá a aparecer.
> Pide confirmación; una vez ejecutado **no hay marcha atrás** (haz backup
> de `estado/` si dudas). No toca `resultados/`.

---

## 8. ¿Cada cuánto se usa?

- **Diario (ideal):** *"Haz la ronda de hoy"* → busca y te deja el resumen.
- **Semanal:** clientes y empresas target (descubrir cosas nuevas).
- **Cuando decidas:** aplicar a una vacante o contactar a alguien.
- **De vez en cuando:** *"¿qué tengo pendiente?"* para no dejar seguimientos
  olvidados.

---

## 9. Restaurar en una computadora nueva

1. Clona el repo y ábrelo con opencode.
2. Las skills viven dentro del repo (`.opencode/skills/`): no hay que
   restaurar nada.
3. Verifica la raíz del proyecto:
   ```bash
   python3 estado/orquestador.py estado
   ```
4. Instala dependencias: `pandoc`, `fonts-liberation`, `python3`.

Los `resultados/` se generan solos; los **recursos los copias con el repo**
(por eso viven en `recursos/`, versionados).

---

> 📂 La raíz se detecta sola con el marcador `.iducdev-root` (o la env
> `IDUCDEV_PROJECT_DIR`). El proyecto puede vivir en cualquier carpeta.