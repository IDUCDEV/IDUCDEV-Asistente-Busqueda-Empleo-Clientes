# Centro de Recursos — Índice Maestro

> **Regla de oro del agente: lee este archivo ANTES de ejecutar cualquier skill.**
> Aquí está todo lo que el asistente **consulta** (recursos de entrada) y todo
> donde **vuelca** sus resultados (`resultados/`). Nunca improvises rutas.

El documento único de uso de este proyecto es **`GUIA.md`** (en la raíz).

---

## 1. Recursos de entrada (lo que el agente CONSULTA)

| Recurso | Ruta | Para qué sirve | Quién lo actualiza |
|---------|------|----------------|--------------------|
| CV base | `recursos/cv/base-isaac-urdaneta.md` | Datos maestros de Isaac (contacto, stack, experiencia, proyectos). Fuente de `linkedin-outreach` y `cv-apply`. | **Tú (humano).** No modificar salvo que el usuario lo pida. |
| CV canónico Español | `recursos/cv/CV-isaac-urdaneta-ES.md` + `.pdf` | CV "estándar" en español listo para enviar. | Tú / generado puntualmente |
| CV canónico Inglés | `recursos/cv/CV-isaac-urdaneta-EN.md` + `.pdf` | CV "estándar" en inglés listo para enviar. | Tú / generado puntualmente |
| Reglas ATS | `recursos/guias/cv-reglas-ats.md` | Prompt/reglas para generar CVs optimizados por vacante (`cv-apply`). | Agente (solo ajuste menor) |
| Guía LinkedIn | `recursos/guias/linkedin.md` | Optimización del perfil de LinkedIn de Isaac. | Tú / agente a demanda |

> **Cómo actualizar tu CV base:** edita `recursos/cv/base-isaac-urdaneta.md`.
> Git lleva el versionado: cada cambio queda en el historial del repo.

---

## 2. Salidas por skill (dónde CADA skill plasma su resultado)

Todo resultado generado por una skill vive bajo `resultados/`.

| Skill | Salida |
|-------|--------|
| `job-search` | `resultados/vacantes/{YYYY-MM-DD}.md` |
| `workana-search` | `resultados/vacantes-workana/{YYYY-MM-DD}.md` |
| `linkedin-hidden-jobs` | `resultados/vacantes-ocultas/{YYYY-MM-DD}-hidden.md` |
| `cv-apply` | `resultados/cv/{cv-base}-{rol}-{empresa}.md` + carta + `.pdf` |
| `linkedin-outreach` | `resultados/mensajes-outreach/{nombre}-{YYYY-MM-DD}.md` |
| `contactar-clientes` | `resultados/mensajes-clientes/{nombre}-{YYYY-MM-DD}.md` |
| `flutter-employers` | `resultados/empresas-target/{YYYY-MM-DD}-empresas.md` + `leads-db.json` |
| `prospectar-clientes` | `resultados/clientes-potenciales/{YYYY-MM-DD}-leads.md` + `leads-db.json` |
| Orquestador (informe) | `resultados/informes/{YYYY-MM-DD}-resumen.md` |

Los `resultados/` se regeneran solos y están ignorados por git.

---

## 3. Empezar aquí

1. **¿Qué hace el asistente?** → `GUIA.md`
2. **¿Dónde está cada salida?** → tabla de la sección 2
3. **Antes de una skill** → consulta `estado/historial.json` (dedup) y este índice.