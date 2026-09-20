---
name: linkedin-outreach
description: Use when the user provides a LinkedIn profile URL and wants to generate a personalized outreach message to ask about Flutter job opportunities. Reads the user's CV base, searches for profile info, and generates a message with one of three tone options.
---

# Skill: linkedin-outreach

Generación de mensajes personalizados para outreach laboral en LinkedIn.

Cuando el usuario pegue una URL de LinkedIn y pida un mensaje de contacto para buscar empleo, ejecuta este workflow.

## Referencias del proyecto (rutas relativas a la raíz)
- **CV Base:** `isaac-urdaneta-base.md`
- **Output dir:** `mensajes-outreach/`

## Workflow

### Fase 1: Leer CV base
Lee `isaac-urdaneta-base.md` para conocer los datos de Isaac.

### Fase 2: Intentar obtener información del perfil

Usa `websearch` con la URL de LinkedIn para buscar información pública de la persona. Intenta obtener:
- Nombre completo
- Empresa actual
- Cargo/rol

Si no obtienes suficiente información, pregunta al usuario los datos faltantes de forma breve.

### Fase 3: Elegir el tono

Pregunta al usuario qué tono prefiere (a menos que ya lo haya especificado):

| Tono | Cuándo usarlo |
|---|---|
| **Directo y natural** (recomendado) | Para la mayoría de los casos. Profesional pero cercano. |
| **Profesional formal** | Empresas grandes, cargos senior, personas mayores. |
| **Casual/amistoso** | Startups, personas jóvenes, perfiles informales. |

### Fase 4: Generar el mensaje

Usa estos templates según el tono seleccionado, interpolando nombre y empresa de la persona objetivo, y los datos de Isaac del CV base.

#### Directo y natural (recomendado)

> Hola [Nombre],
>
> Gracias por conectar. Estoy en búsqueda activa como Flutter Engineer y veo que trabajas en [Empresa]. ¿Sabes si hay vacantes abiertas para Flutter o conoces a alguien de recruiting con quien pueda conversar? Cualquier referencia me sirve muchísimo.
>
> Por cierto, por si te sirve de referencia: mi stack principal es Flutter, Dart, Clean Architecture, BLoC y Supabase, además de experiencia previa en React/Next.js — con [X] año especializado en Flutter y [Y]+ en desarrollo de software.
>
> ¡Gracias!

#### Profesional formal

> Estimado/a [Nombre],
>
> Agradezco la conexión. Mi nombre es Isaac Urdaneta, Flutter Engineer con experiencia en desarrollo de aplicaciones móviles y actualmente en búsqueda activa de oportunidades. Veo que formas parte de [Empresa], y quería preguntarte si tienes conocimiento de alguna vacante abierta para Flutter en tu equipo, o si puedes referirme con alguien del área de recruiting.
>
> Mi stack incluye Flutter, Dart, Clean Architecture, BLoC, Supabase y PostgreSQL, además de experiencia previa en React/Next.js. Cuento con [X] año de experiencia especializada en Flutter y más de [Y] años en desarrollo de software.
>
> Quedo atento a cualquier información. ¡Saludos!

#### Casual / amistoso

> ¡Hola [Nombre]!
>
> Gracias por conectar, gusto tenerte en mi red. Estoy buscando oportunidades como Flutter Developer y vi que trabajas en [Empresa] — qué bien. ¿Sabes si hay cupos abiertos para Flutter por allá o conoces a alguien de recruiting con quien pueda hablar?
>
> Mi stack: Flutter, Dart, Clean Architecture, BLoC, Supabase, además de experiencia en React/Next.js. [X] año en Flutter, [Y]+ en software en general.
>
> ¡Gracias!, quedo atento.

### Fase 5: Guardar y mostrar

1. Guarda el mensaje en:
   ```
   mensajes-outreach/{nombre-normalizado}-{YYYY-MM-DD}.md
   ```
   Donde `nombre-normalizado` es el nombre de la persona en lowercase con guiones (ej: juan-perez).

2. Registra el contacto en el historial central para no repetir. El orquestador
   creará **automáticamente** la tarea de seguimiento a los 3 días:
   ```bash
   python3 estado/orquestador.py marcar outreach "<url-del-perfil>" enviado
   ```
   (Si solo quieres registrar sin marcar, usa el helper directo:)
   ```bash
   python3 - <<'EOF'
   import sys
   sys.path.insert(0, "estado")
   from tracker import Historial
   h = Historial()
   h.add("outreach", "<url-del-perfil>", meta={"nombre": "...", "empresa": "...", "estado": "nuevo", "tono": "..."})
   EOF
   ```

3. Muestra el mensaje al usuario listo para copiar y pegar.
4. Indica la ruta del archivo guardado.