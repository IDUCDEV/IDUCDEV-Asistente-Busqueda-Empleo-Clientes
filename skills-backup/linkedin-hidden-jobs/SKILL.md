---
name: linkedin-hidden-jobs
description: Busca el "hidden job market" de LinkedIn (posts donde la gente publica vacantes de Flutter/Dart, no avisos oficiales). Queries mixtas español/inglés para captar reclutadores LATAM y global. Filtra remoto/LATAM/español/inglés, últimos 3 días. Extrae URL directa del post vía menú de 3 puntos. Genera markdown en vacantes-ocultas/.
---

# Skill: linkedin-hidden-jobs

Busca oportunidades laborales publicadas en **posts de LinkedIn** (no en la sección de empleos) usando el navegador con sesion autenticada del usuario.

Cuando el usuario invoque esta skill, ejecuta TODO el workflow:

1. Abrir navegador o pedir al usuario que se loguee en LinkedIn si no lo esta
2. Navegar LinkedIn Search y buscar posts con las queries definidas
3. Extraer posts del feed de resultados
4. Filtrar: ofertas reales + remoto/LATAM/espanol
5. Generar archivo markdown
6. Mostrar resultado al usuario
7. Indicar que puede aplicar con `cv-apply`

---

## Paso 0: Verificar/Abrir navegador con sesion de LinkedIn

Usa `chrome-devtools_list_pages` para ver si ya hay paginas abiertas.

- Si no hay pagina abierta o LinkedIn no esta logueado:
  - Crea nueva pagina con `chrome-devtools_new_page` apuntando a `https://www.linkedin.com/feed/`
  - Indica al usuario: *"Por favor inicia sesion en LinkedIn en el navegador que se abrio. Una vez logueado, avisame para continuar."*
  - Espera confirmacion del usuario
  - Verifica que la URL actual sea `linkedin.com/feed` (logueado)

- Si ya hay pagina con LinkedIn logueado: usala directamente

## Queries de búsqueda (ejecutar en orden, una por una)

Para cada query, navega a la URL de busqueda de LinkedIn y extrae los posts visibles.

**URL base de busqueda:**
```
https://www.linkedin.com/search/results/content/?keywords={query}&origin=GLOBAL_SEARCH_HEADER&sid=s%2C~%3Afsb&datePosted=r259200
```

El parametro `datePosted=r259200` filtra ultimos 3 dias.
⚠️ LinkedIn auto-encodifica el valor a `%22r259200%22` (con dobles comillas). Esto es normal y el filtro funciona parcialmente: muestra posts recientes del periodo + algunos resultados antiguos promocionados. No modificar la URL.

**Queries a ejecutar (TODAS) — mezcla de español e inglés para max cobertura:**

1. `flutter vacante remoto`
2. `flutter contratando desarrollador`
3. `flutter oferta laboral remoto`
4. `flutter buscamos desarrollador`
5. `flutter empleo remoto latam`
6. `dart desarrollador remoto contratando`
7. `flutter hiring remote latam`
8. `flutter job opening remote`

### Procedimiento por query:

#### A. Extraer datos del snapshot

1. Navegar a la URL construida con `chrome-devtools_navigate_page`
2. Esperar 3-5s con `chrome-devtools_wait_for` (espera texto "Publicación en el feed")
3. Tomar snapshot con `chrome-devtools_take_snapshot`
4. Del snapshot extraer para cada post:
   - Autor del perfil (link con url `linkedin.com/in/`)
   - Texto del post
   - Fecha (buscar texto como "8 h", "16 h", "1 d", "2 d", "1 sem", "2 sem", "1 mes", "2 meses")
   - Reacciones (numero tras las reacciones)
5. Hacer scroll con `chrome-devtools_press_key` key="PageDown" si hay pocos resultados, repetir snapshot
6. Si hay paginación, navegar a siguiente página

#### B. Extraer URL del post — OBLIGATORIO para cada post (método del menú de 3 puntos)

LinkedIn NO expone la URL directa del post en el feed de resultados. **Debes extraer la URL para CADA post incluido en el output, sin excepción.**

La URL extraída va en el campo `**LinkedIn:**` del markdown, NO en `**Link:**`.

Procedimiento:

1. Para cada post que vayas a incluir, localizar el botón "Abrir el menú de controles para la publicación de {autor}" (es un button expandable con icono "...")
2. Hacer clic en ese botón con `chrome-devtools_click` — se expande un menú contextual con opciones
3. Tomar snapshot para verificar que el menú apareció (debe contener "Copiar enlace a la publicación")
4. Hacer clic en el menuitem "Copiar enlace a la publicación" con `chrome-devtools_click`
5. Inmediatamente aparecerá un alert/snackbar con "El enlace se ha copiado" y un link "Ver publicación"
6. Tomar snapshot — el link "Ver publicación" contiene la URL completa del post
7. Extraer la URL del link "Ver publicación"
8. Cerrar el snackbar (click en "Cerrar", "Close", o presionar Escape)
9. Si el menú no se cierra tras el click, presionar Escape
10. **Repetir para CADA post, sin saltarse ninguno**

**Formato de la URL extraída:**
```
https://www.linkedin.com/posts/{username}_{activity-hash}/?utm_source=share&utm_medium=member_desktop&rcm=...
```

## Filtros (aplicar en orden)

### 1. Validar URL
Solo URLs que empiecen con `linkedin.com/posts/...` o `www.linkedin.com/posts/...`
Tambien validar URLs de `linkedin.com/company/...` (posts de empresa)

### 2. Identificar oferta REAL (no artículo, no promocion)
El texto del post debe contener AL MENOS UNA de estas frases:
- `hiring`, `"we're hiring"`, `"we are hiring"`, `"looking for"`, `"job opening"`, `"join our team"`, `"open position"`, `"now hiring"`
- `vacante`, `contratando`, `"estamos buscando"`, `"se busca"`, `oportunidad`, `necesitamos`, `empleo`
- `contrato`, `remoto`, `position`, `opening`, `role`

### 3. Filtrar remoto/LATAM
El texto del post debe contener AL MENOS UNA de:
- `remote`, `remoto`, `remota`, `work from home`, `trabajo desde casa`, `home office`
- `latam`, `"latin america"`, `latinoamerica`, `worldwide`, `"anywhere"`, `"United States"` (si acepta LATAM)

### 4. Detectar español o ingles
Si el post contiene palabras en espanol (articulos, preposiciones como `el`, `la`, `de`, `en`, `para`, `que`, `con`, `por`, `desarrollador`, `experiencia`, `equipo`, `busca`, `trabajo`, `remoto`, `empresa`, `salario`, `requisitos`, `funciones`, `ingeniero`) incluirlo.
Si esta en ingles, incluir igual si las palabras clave de hiring/remote estan presentes.

### 5. Deducir duplicados
Si la misma URL aparece en multiples queries, mantener solo una ocurrencia. Si el mismo post aparece con distinta URL pero mismo autor y contenido, deduplicar.

### 6. Limite temporal — EXIGENTE
LinkedIn muestra resultados del filtro `datePosted=r259200` pero su algoritmo de relevancia incluye posts promocionados fuera del periodo. **Debes filtrar manualmente por fecha:**

✅ **Aceptar** si la fecha es: `{n} h`, `{n}h`, `{n} d`, `{n}d`, `{n} día`, `{n} dias`, `hace {n} hora`, `hace {n} horas`, `hace {n} día`, `hace {n} días` (donde `{n} < 4`)

❌ **Rechazar** si la fecha es: `{n} sem`, `{n} semana`, `hace {n} semanas`, `{n} mes`, `{n} meses`, `hace {n} mes`, `hace {n} meses`, `{n} año`, `{n} anos`

❌ **Rechazar** si muestra fecha calendario (ej: "15 jun 2026") que sea > 3 días atrás

Si no hay fecha visible, marcar con ⚠️ y decidir por contenido.

---

## Output: formato del markdown

```markdown
# Vacantes Ocultas LinkedIn — {fecha}

> Busqueda en posts de LinkedIn · {hora} UTC
> Remoto/LATAM/Global · Ultimos 3 dias

---

## Resultados ({n})

### 1. {titulo del puesto inferido}
**Autor:** {nombre del autor}
**Perfil:** {url del perfil del autor}
**Empresa:** {empresa inferida del perfil o del post}
**Post:** {snippet del texto del post (max 300 chars)}
**LinkedIn:** [{linkedin_post_url}]({linkedin_post_url})
{si el post tiene enlace explicito para aplicar (DM, mailto, formulario externo):}
**Link:** [{url_aplicacion}]({url_aplicacion})
**Antigüedad:** {fecha relativa}
**Ubicación:** {ubicacion si se menciona}
**Tags:** {hashtags relevantes}
**Query:** {query que encontro este post}
`[Aplicar con cv-apply]`

### 2. ...
```

**Reglas:**
- `**LinkedIn:**` → **SIEMPRE requerido**. Es la URL del post extraída vía menú de 3 puntos (sección B).
- `**Link:**` → **SOLO si existe** enlace explícito en el post para aplicar (DM, mailto, formulario externo, web externa). No inventar. Si no existe, omitir este campo.
- `**Antigüedad:**` y `**Ubicación:**` → incluir si están disponibles.
- `**Tags:**` → extraer hashtags del post.
- `**Query:**` → indicar qué query original encontró este post (útil para saber si fue query en español o inglés).

---

## Archivo de salida

```
/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/vacantes-ocultas/{YYYY-MM-DD}-hidden.md
```

Si se invoca varias veces el mismo dia, sobrescribe el archivo.

---

## Dedup central (NO repetir posts)

Antes de escribir el archivo, consulta y actualiza
`/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/estado/historial.json`:

1. Lee las claves ya registradas de la categoría `posts_linkedin` (URL del post).
2. Para cada post extraído, si su URL ya está → **omítelo** (no listarlo).
3. Los que sean nuevos → registrarlos con estado `nuevo` y meta
   (`autor`, `empresa`, `url`, `snippet`).

Helper sugerido (Python):

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "/home/iducdev/Escritorio/IDUCDEV -- Asistente de busqueda de empleo y clientes/estado")
from tracker import Historial
h = Historial()
# consultar: h.is_known("posts_linkedin", url)
# registrar: h.add("posts_linkedin", url, meta={"autor": ..., "url": url})
EOF
```

---

## Pipeline post-busqueda

Cuando el usuario vea la lista y quiera aplicar a una:

1. Usuario pasa el link o descripcion
2. Cargar skill `cv-apply`
3. Ejecutar workflow de `cv-apply`
