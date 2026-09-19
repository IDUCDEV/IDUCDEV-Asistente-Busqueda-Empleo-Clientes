---
name: prospectar-clientes
description: Genera leads de negocios venezolanos que necesiten desarrollo web, apps Flutter o automatizaciones n8n. Busca en Overpass API, infoguia y web search. Visita websites, analiza con IA y genera markdown con scoring. Sin APIs de pago, sin n8n.
---

# prospectar-clientes — Pipeline de prospección de leads (VE)

Reemplaza el flujo de n8n. Busca negocios en Venezuela, analiza si necesitan servicios digitales y genera un markdown listo para usar.

## Archivos de referencia

- **DB de leads (historial):** `/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/clientes-potenciales/leads-db.json`
- **Output del día:** `/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/clientes-potenciales/{YYYY-MM-DD}-leads.md`

---

## Resumen del pipeline

```
FASE 1: GENERAR LEADS
  Overpass API ──┐
  infoguia.com ──┼──→ Deduplicar → Normalizar
  web search ────┘

FASE 2: VISITAR Y ANALIZAR WEBSITE
  Por cada lead con web → abrir en navegador → screenshot → evaluar

FASE 3: SCORING CON IA
  score 0-100 | service_match | pain_points | icebreaker | channel

FASE 4: OUTPUT
  leads-db.json (historial)
  {YYYY-MM-DD}-leads.md (reporte del día)
```

---

## FASE 1: Generación de leads

### 1.1 — Overpass API (OpenStreetMap)

Negocios venezolanos con sitio web y teléfono declarados en OSM.

**Endpoint:**
```
POST https://overpass-api.de/api/interpreter
Content-Type: application/x-www-form-urlencoded
Body: data=[out:json];area["ISO3166-1"="VE"]->.a;nwr(area.a)[~"^(shop|amenity|office|craft)$"~"."][website~"."];out center 100;
```

Usar `webfetch` con método POST. Si no funciona, probar con query simplificada:
```
data=[out:json];area["name"="Venezuela"]->.a;nwr(area.a)[website~"."][phone~"."];out center 50;
```

**Parsear respuesta:** Extraer del JSON:
- `name` → `tags.name`
- `phone` → `tags.phone` o `tags["contact:phone"]`
- `website` → `tags.website` o `tags["contact:website"]`
- `address` → concatenar `tags["addr:street"]`, `tags["addr:city"]`, `tags["addr:state"]`
- `industry` → `tags.shop` o `tags.amenity` o `tags.office` o `tags.craft`
- `source` → `"overpass"`

### 1.2 — infoguia.com (directorio comercial VE)

Abrir `chrome-devtools_navigate_page` para scrapear listados de infoguia.

**URL base:**
```
https://infoguia.com/categoria.asp?cat={CAT}&estado={ESTADO}&pag={N}
```

**Categorías a scrapear (ejecutar varias):**

| Categoría | Código | Prioridad |
|-----------|--------|-----------|
| Restaurantes | RESTAURANTES | Alta |
| Clínicas | CLINICAS | Alta |
| Gimnasios | GIMNASIOS | Alta |
| Institutos Educativos | INSTITUTOS_EDUCATIVOS | Alta |
| Tiendas | TIENDAS | Media |
| Barberías | BARBERIAS | Media |
| Inmobiliarias | INMOBILIARIAS | Media |
| Hoteles | HOTELES | Media |
| Veterinarias | VETERINARIAS | Media |
| Talleres | TALLERES | Baja |

**Estados disponibles:**
`DTTO_CAPITAL` (Caracas), `MIRANDA`, `CARABOBO`, `ZULIA`, `LARA`, `BOLIVAR`, `ARAGUA`, `ANZOATEGUI`, `NUEVA_ESPARTA`, `TACHIRA`, `MERIDA`

**Procedimiento:**
1. Navegar a `https://infoguia.com/categoria.asp?cat=RESTAURANTES&estado=DTTO_CAPITAL&pag=1`
2. Tomar snapshot con `chrome-devtools_take_snapshot`
3. Extraer del snapshot: nombre, teléfono, dirección de cada resultado
4. Hacer clic en cada link de negocio para obtener más detalles si es necesario
5. Repetir para cada categoría y paginación (páginas 1-3)
6. Si hay paginación, navegar a `&pag=2`, `&pag=3`

**Selectores típicos (pueden variar, inspeccionar snapshot real):**
- Nombre: link dentro del div de resultado
- Teléfono: texto que contiene números de teléfono
- Dirección: texto con dirección

**Output por lead:**
```json
{
  "name": "Nombre del negocio",
  "phone": "+58 412...",
  "address": "Caracas, Venezuela",
  "industry": "restaurante",
  "source": "infoguia"
}
```

### 1.3 — Web search (directorios y listados)

Usar `websearch` para encontrar negocios venezolanos por rubro.

**Queries de búsqueda:**
```
negocios venezolanos con sitio web necesitan actualizar desarrollar app movil
restaurantes Venezuela necesitan app delivery
clínicas Venezuela necesitan sistema agendar citas
gimnasios Venezuela buscan app membresías
escuelas institutos Venezuela buscan plataforma educativa
tiendas Venezuela buscan e-commerce tienda online
hoteles posadas Venezuela buscan sistema reservas booking
inmobiliarias Venezuela buscan app catálogo propiedades
```

De cada resultado de `websearch`, extraer:
- Nombre del negocio
- URL del sitio web
- Descripción si está disponible

**Nota:** `websearch` devuelve resultados con título, snippet y URL. Priorizar los que tienen website visible.

### 1.4 — Deduplicar leads (manual)

Comparar los leads obtenidos de las 3 fuentes. Eliminar duplicados por nombre (normalizado: minúsculas, sin tildes, sin espacios extra).

Para mantener estado entre sesiones, leer `leads-db.json` al inicio y cruzar contra nuevos leads. Los que ya existen se saltan.

Además, cruzar contra el historial central del proyecto:
`/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/estado/historial.json`
(categoría `clientes`, clave: dominio o nombre normalizado), usando el helper:

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/estado")
from tracker import Historial
h = Historial()
# consultar: h.is_known("clientes", dominio_o_nombre)
# registrar: h.add("clientes", dominio_o_nombre, meta={"nombre": ..., "web": ..., "rubro": ...})
EOF
```

Así ningún cliente se repite entre sesiones ni entre skills.

### 1.5 — Normalizar a formato común

Cada lead final debe tener esta estructura:
```json
{
  "name": "Nombre del negocio",
  "phone": "+58 412-1234567",
  "website": "https://ejemplo.com",
  "address": "Caracas, Venezuela",
  "industry": "restaurante",
  "source": "overpass | infoguia | web_search",
  "score": 0,
  "service": "",
  "pain_points": "",
  "icebreaker": "",
  "channel": "",
  "status": "new",
  "first_seen": "2026-06-24",
  "last_checked": "2026-06-24",
  "website_analysis": ""
}
```

Los nuevos leads inician con `score: 0` (sin analizar).

---

## FASE 2: Visitar website y analizar visualmente

Por cada lead que tenga `website` y esté en estado `new` (o que no se haya analizado antes):

### Procedimiento:

1. Abrir nueva página con `chrome-devtools_new_page` apuntando a la URL del negocio
2. Esperar carga (usar `chrome-devtools_wait_for` con timeout de 10s)
3. Tomar screenshot con `chrome-devtools_take_screenshot`
4. Analizar visualmente el screenshot:
   - **Diseño:** ¿Moderno o anticuado? ¿Responsive? ¿Se ve bien en mobile?
   - **Funcionalidad:** ¿Tiene carrito/tienda online? ¿Sistema de reservas? ¿Blog? ¿Contacto?
   - **Tecnologías perceptibles:** ¿WordPress? ¿HTML estático? ¿SPA?
   - **Problemas detectados:** ¿Lento? ¿Mal diseño? ¿Sin mobile? ¿Sin CTA claro?
5. Registrar análisis en `website_analysis`
6. Cerrar página con `chrome-devtools_close_page`

### Criterios de evaluación visual:

| Señal | Indica |
|-------|--------|
| Sitio anticuado, no responsive | Necesita web moderna → `web_app` |
| No tiene sitio web (solo redes) | Necesita web → `web_app` |
| Sitio ok pero sin app móvil | Necesita app → `flutter_app` |
| Procesos manuales visibles (pedidos por WhatsApp, reservas por tlf) | Necesita automatización → `automation` |
| Sitio ok pero sin e-commerce vendiendo presencial | Necesita tienda online → `web_app` |
| Todo bien, difícil de mejorar | Score bajo, seguir adelante |

Si el website no carga o da error, anotar como "No disponible" y continuar con score basado en nombre/rubro únicamente.

---

## FASE 3: Scoring con IA

Analizar cada lead (con o sin website analizado) y asignar puntaje.

### Prompt para Gemini/IA:

```
Eres un asistente de prospeccion para IDUCDEV, un desarrollador freelance venezolano.

SERVICIOS QUE OFRECE:
1. Desarrollo web (sitios, plataformas, e-commerce)
2. Apps moviles con Flutter (iOS + Android)
3. Automatizaciones con n8n
4. Diseño UI/UX

DATOS DEL LEAD:
- Nombre: {name}
- Rubro/Industria: {industry}
- Tiene web: {website} (Sí/No)
- Analisis visual del sitio: {website_analysis}

CRITERIOS DE SCORING:
- Score 70-100: Necesita claramente uno o mas servicios (tiene web anticuada, no tiene app, procesos manuales)
- Score 40-69: Podria necesitar, requiere mas investigacion (tiene web moderna pero le falta algo)
- Score <40: Probablemente no necesita (tiene todo bien o es muy pequeno)

Responde SOLO este JSON sin ningun otro texto:
{
  "score": 0-100,
  "service": "flutter_app" | "web_app" | "automation" | "multiple" | "none",
  "pain_points": ["punto"],
  "icebreaker": "Frase personalizada en espanol, natural, que demuestre que viste su negocio",
  "channel": "whatsapp" | "email" | "linkedin"
}
```

### Reglas de scorers:

- **70+ hot** → Contactar hoy. Tiene necesidad clara y urgente.
- **40-69 warm** → Contactar esta semana. Potencial pero no urgente.
- **<40 cold** → Guardar para seguimiento futuro o descartar.

Si no hay website ni suficiente información, score máximo 40 (cold) hasta investigar más.

### Parsear respuesta:

Del JSON de la IA extraer: `score`, `service`, `pain_points` (array → string separado por `; `), `icebreaker`, `channel`.

---

## FASE 4: Output markdown

### Actualizar leads-db.json

Leer el archivo `leads-db.json` si existe. Agregar los nuevos leads o actualizar los existentes. Guardar el JSON actualizado.

Estructura del JSON:
```json
{
  "leads": [
    {
      "name": "...",
      "phone": "...",
      "website": "...",
      "address": "...",
      "industry": "...",
      "source": "...",
      "score": 85,
      "service": "flutter_app",
      "pain_points": "No tiene app movil; sitio web anticuado",
      "icebreaker": "Vi tu restaurante en la web, tienes menu digital pero sin app...",
      "channel": "whatsapp",
      "status": "new | contacted | replied | closed",
      "first_seen": "2026-06-24",
      "last_checked": "2026-06-24",
      "website_analysis": "Sitio WordPress, no responsive, carga lenta"
    }
  ]
}
```

### Generar markdown del día

```markdown
# Leads potenciales — Venezuela — {YYYY-MM-DD}

> Generado por prospectar-clientes skill
> Fuentes: Overpass API, infoguia.com, web search
> Total leads: {n}

---

## Leads calientes (score ≥ 70)

### 1. {nombre del negocio}
- **Rubro:** {industria}
- **Contacto:** {teléfono} | [{website}]({website})
- **Score:** {n}/100 🔥
- **Servicio:** {flutter_app | web_app | automation | multiple}
- **Pain points:** {detectados}
- **Icebreaker:** "{frase personalizada}"
- **Canal recomendado:** {whatsapp | email | linkedin}
- **Análisis web:** {notas del análisis visual}
- **Fuente:** {overpass | infoguia | web_search}
- **Primera vez visto:** {fecha}

### 2. ...

---

## Leads tibios (40 ≤ score < 70)

### 3. ...

---

## Leads fríos (score < 40)

### 4. ...

---

## Acciones recomendadas

| Prioridad | Lead | Servicio | Canal | Icebreaker |
|-----------|------|----------|-------|------------|
| 🔥 Alta | ... | flutter_app | WhatsApp | ... |
| 🔥 Alta | ... | multiple | WhatsApp | ... |
| 🟡 Media | ... | web_app | WhatsApp | ... |

---

## Historial

Leads procesados hasta hoy: {n} totales
Leads calientes activos: {n}
Leads contactados: {n}
```

---

## Estado persistente: leads-db.json

Se usa para:
1. No repetir leads ya procesados en ejecuciones anteriores
2. Mantener historial de estado (new → contacted → replied → closed)
3. Enriquecer gradualmente (un lead puede ser "cold" hoy, pero si aparece de nuevo con más datos, se re-analiza)

### Flujo de persistencia:

1. Al iniciar, leer `leads-db.json` (si no existe, array vacío)
2. Después de generar nuevos leads, comparar por `name` (normalizado):
   - Si el nombre NO existe en DB → agregar como nuevo (con `status: "new"`)
   - Si el nombre ya existe → NO duplicar (saltar)
3. Después del scoring, actualizar `score`, `service`, `pain_points`, `icebreaker`, `channel`, `website_analysis`, `last_checked`
4. Guardar `leads-db.json` actualizado
5. Generar markdown solo con los leads nuevos del día (los que tienen `first_seen === today`)

---

## Ejecución

```bash
# Invocar desde opencode:
# "prospectar clientes" o "busca leads"
```

Cuando el usuario invoque la skill, ejecutar TODO el flujo en orden:
1. FASE 1 → Generar leads de las 3 fuentes
2. FASE 2 → Visitar websites de leads nuevos
3. FASE 3 → Scorer cada lead
4. FASE 4 → Actualizar DB + generar markdown
5. Mostrar el markdown al usuario

### Notas por fuente:

**Overpass API:** Puede tardar 5-10s en responder. Si falla, reintentar 1 vez con query más simple. Si sigue fallando, continuar sin Overpass.

**infoguia:** No hacer más de 15 requests por ejecución para no saturar. Priorizar categorías Alta primero. Si la estructura HTML no coincide con lo esperado, inspeccionar el snapshot y ajustar la extracción.

**web search:** Si devuelve pocos resultados para una query, probar variantes más genéricas (ej: "restaurantes Venezuela app" → "Venezuela restaurantes tecnología").

### Límites por ejecución:
- Máximo 10-12 leads por tanda (para no saturar el browser ni la IA)
- Si hay más leads disponibles, procesar los de mayor prioridad y dejar el resto para la próxima ejecución
- Máximo 5 websites visitados por ejecución (los de mayor score potencial)

---

## Post-ejecución

Cuando el usuario vea la lista y quiera actuar sobre un lead:

1. Usuario dice "contactar {nombre}" o "aplicar a {nombre}"
2. Copiar el **icebreaker** y el **canal recomendado** del markdown
3. Si el usuario quiere generar un outreach message completo, cargar `cv-apply` skill adaptado para prospección
4. El usuario contacta manualmente y actualiza el estado en `leads-db.json` (o el skill lo hace)

### Comandos rápidos (vía opencode):
- `"contactar {lead_name}"` → mostrar icebreaker + canal + sugerir outreach
- `"marcar contactado {lead_name}"` → actualizar DB a `status: contacted`
- `"ver historial"` → mostrar leads-db.json resumido
- `"analizar {url}"` → analizar un website específico como lead manual
