# Diagramas — Asistente IDUCDEV (Flujos completos)

Diagramas en **Mermaid** ([ver en GitHub](https://github.com) o copiar cada
bloque en https://mermaid.live para editarlos). Vista renderizada:
`docs/diagramas.html` (ábrelo en el navegador).

---

## 0. Arquitectura general

```mermaid
flowchart LR
    USUARIO["👤 Tú <br/>hablas en lenguaje natural"]

    PUERTA[fa:fa-sitemap asistente-empleo-clientes<br/>puerta de entrada única]

    subgraph CEREBRO["🧠 Cerebro · estado/"]
        HISTORIAL["historial.json<br/>dedup central (nunca repetir)"]
        TAREAS["tareas.json<br/>bandeja + seguimientos D+3 / D+7"]
        RONDAS["rondas.json<br/>bitácora de rondas"]
        COLA["cola_envios.json<br/>mensajes de venta en cola"]
        ORQ[orquestador.py / tracker.py / cola_envios.py / enviar_email.py]
    end

    subgraph RECURSOS["📂 recursos/ (los mantiene el humano)"]
        INDICE["INDICE.md · CV base · reglas ATS · guías"]
    end

    subgraph RESULTADOS["📤 resultados/ (se regeneran)"]
        VACANTES["vacantes/ · vacantes-workana/ · vacantes-ocultas/"]
        CLIENTES["clientes-potenciales/ · empresas-target/ · leads-db.json"]
        MSG["mensajes-outreach/ · mensajes-clientes/"]
        CV["cv/ (CV + carta + PDF)"]
        INF["informes/ (resumen diario)"]
    end

    USUARIO --> PUERTA
    PUERTA -->|consulta| INDICE
    PUERTA -->|dedup antes de mostrar| HISTORIAL
    PUERTA -->|registra después| HISTORIAL
    CEREBRO --> RESULTADOS
    RESULTADOS --> PUERTA
```

---

## 1. "Haz la ronda de hoy" — Descubrimiento (empleos + clientes)

```mermaid
flowchart TD
    INICIO([¡Haz la ronda de hoy!]) --> PASO1

    PASO1["1️⃣ job-search<br/>vacantes Flutter/remoto LATAM<br/><i>scripts · sin navegador</i>"]
    PASO2["2️⃣ workana-search<br/>proyectos freelance<br/><i>scripts · sin navegador</i>"]

    PASO1 & PASO2 --> ORQ["estado/orquestador.py ronda --empleos<br/>(lanza 1 y 2 + anota rondas.json)"]

    ORQ --> PREGUNTA{¿Autorizas<br/>el navegador?}

    PREGUNTA -- "No" --> ORACULO
    PREGUNTA -- "Sí" --> NAV["🧭 Navegador"]

    NAV --> H3["3️⃣ linkedin-hidden-jobs<br/>mercado oculto de LinkedIn"]
    NAV --> H4["4️⃣ prospectar-clientes<br/>leads de negocios VE"]
    NAV --> H5["5️⃣ flutter-employers<br/>empresas target <i>(semanal)</i>"]

    H3 --> REG3["registrar linkedin-hidden-jobs<br/>--nuevas N"]
    H4 --> REG4["registrar prospectar-clientes<br/>--nuevas N"]
    H5 --> REG5["registrar flutter-employers<br/>--nuevas N"]

    ORACULO["⚠️ sin navegador: solo fases 1-2"]

    REG3 & REG4 & REG5 & ORACULO --> INFORME["informe<br/>→ resultados/informes/fecha-resumen.md"]
    INFORME --> DEDUP["🧠 historial.json: todo lo nuevo registrado<br/>(omite lo ya visto)"]
```

---

## 2. Empleo — de la vacante a la aplicación/contacto

```mermaid
flowchart TD
    subgraph DESC["Descubrimiento"]
        RONDA["ronda → vacantes listadas<br/>en resultados/vacantes/*.md"] --> ELIGE
    end

    ELIGE{¿Qué hago con la vacante?}

    ELIGE -->|"Aplica a {vacante}"| APPLY[("cv-apply")]
    APPLY --> CVGEN["CV optimizado ATS + carta + PDF<br/>→ resultados/cv/"]
    CVGEN --> MARKAPP["orquestador.py marcar vacantes … applied"]
    MARKAPP --> T7["🗓️ Seguimiento automático D+7"]
    T7 --> BANDEJA["bandeja de tareas (tareas.json)<br/>'¿qué tengo pendiente?'"]

    ELIGE -->|"Contacta a {perfil LinkedIn}"| OUTREACH[("linkedin-outreach")]
    OUTREACH --> MSGO["mensaje personalizado<br/>→ resultados/mensajes-outreach/"]
    MSGO --> MARKOUT["orquestador.py marcar outreach … enviado"]
    MARKOUT --> T3["🗓️ Seguimiento automático D+3"]
    T3 --> BANDEJA
```

---

## 3. Clientes — prospectar → generar → enviar (uno por uno)

```mermaid
flowchart TD
    A["prospectar-clientes<br/><i>descubrimiento semanal</i>"] --> B["leads-db.json + leads.md<br/>scoring + pain points + canal"]
    B --> C[("🧾 contactar-clientes<br/>'contacta a {cliente}'")]

    C --> D["mensaje personalizado .md<br/>→ mensajes-clientes/"]
    D --> E[("📥 ENCOLA: cola_envios.py add<br/>lead status: en_cola")]

    E --> F[("📤 enviar-clientes /enviar<br/>'envía los pendientes'")]

    F --> G{"Ronda uno por uno<br/><i>¿Qué hago con este lead?</i>"}

    G -->|"OK"| ENVIAR["enviar por canal"]
    G -->|"modificar"| MOD["editar .md + cola sincronizada<br/>cola_envios.py editar --cuerpo-file"]
    MOD --> VER["ver <id> (muestro versión final)"] --> G
    G -->|"saltar"| SALTAR["queda pendiente<br/>para la próxima ronda<br/><i>no marca nada</i>"] --> SIG
    G -->|"parar"| PARAR["termina la ronda<br/>el resto queda pendiente"] --> REG

    ENVIAR --> EMAIL["✉️ email · SMTP Gmail<br/>100% automático"]
    ENVIAR --> WA["💬 WhatsApp Web<br/>?phone=&text= + Enter<br/>pausa 15-35s"]
    ENVIAR --> LI["💼 LinkedIn · semi<br/>pego el texto, tú pulsas Enter"]

    EMAIL --> OKOK{"¿Envió bien?"}
    WA --> OKOK
    LI --> OKOK

    OKOK -- "✅ sí" --> MARK["enviado + contactado (D+3)<br/>cola: enviado · historial: contactado<br/>leads-db: status contacted"]
    MARK --> SIG["siguiente lead (chequea cupo 12/día)"]
    SIG -->|"¿queda cola y cupo?"| G

    OKOK -- "❌ error (email falló / nº no registrado)" --> ERR["cola: error (reintentable)<br/><b>sin</b> contactado ni D+3"]
    ERR --> SIG

    REG["registrar enviar-clientes --nuevas N + informe"]
```

---

## 4. Ciclo de vida del estado (historial.json) y de la cola

```mermaid
stateDiagram-v2
    [*] --> nuevo : descubierto en una ronda
    nuevo --> revisado : tú lo ves / lo revisas
    revisado --> en_proceso : decides accionar
    en_proceso --> aplicado : cv-apply (D+7)
    en_proceso --> enviado : outreach / contacto (D+3)
    aplicado --> respuesta : te contestan
    enviado --> respuesta : te contestan
    aplicado --> descartado
    enviado --> descartado
    respuesta --> [*]
    descartado --> [*]
```

```mermaid
stateDiagram-v2
    direction LR
    [*] --> pendiente : contactar-clientes encola
    pendiente --> enviado : envío efectivo (D+3 → contactado)
    pendiente --> error : SMTP falla / nº no registrado
    pendiente --> pendiente : "saltar" (siguiente ronda)
    error --> pendiente : reintento
    enviado --> [*]
```

---

## 5. Seguimientos automáticos (bandeja D+3 / D+7)

```mermaid
sequenceDiagram
    autonumber
    participant U as Tú
    participant A as Asistente
    participant O as orquestador.py
    participant T as tareas.json

    A->>O: marcar <cat> <key> enviado/contactado/applied
    O->>O: registrar estado + fecha
    O->>T: crear tarea de seguimiento<br/>(D+3 contagentes · D+7 aplicaciones)
    Note over U,T: "unos días después…"
    U->>A: ¿qué tengo pendiente?
    A->>O: tareas / seguimientos (vencidos + próximos)
    O-->>A: lista de seguimientos con vencimiento
    A-->>U: "⚠️ vence hoy: seguimiento de Clínica CCCT"
```

---

**Reglas que aplican a todos los diagramas:**

1. **Nunca repetir:** historial dedup en toda skill (consultar + registrar).
2. Resultados **siempre** en `resultados/<skill>/`, nunca en `recursos/`.
3. Navegador **solo con autorización** explícita.
4. Clientes: `contactado`/D+3 solo tras **envío efectivo** (errores reintentables).
5. Límite 12 envíos/día, pausa 15-35s entre WhatsApp.