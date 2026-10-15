---
name: aplicar-wellfound
description: Automatiza la aplicación uno por uno a vacantes de Wellfound, con validación humana. Parsea el bloque Wellfound de resultados/vacantes/2026-10-09.md, encola en estado/cola_aplicaciones.json, determina si vale la pena con filtro_vacante.py + Fase 2 (cv-apply), genera CV+PDF+carta en resultados/cv/, presenta el paquete al usuario para ok/modificar/saltar/parar (o para aplicar asistido con navegador), y solo tras envío efectivo marca la vacante como applied (crea seguimiento D+7). Sigue el principio "uno por uno" y nunca evade protecciones anti-bot.
---

# Skill: aplicar-wellfound

Aplica **uno por uno** a vacantes de Wellfound. No genera lote: valida cada candidato con el usuario antes de pasar al siguiente.

## Fuentes
- Listado: `resultados/vacantes/2026-10-09.md`, sección **`## Wellfound`** (58 entradas).
- Cola: `estado/cola_aplicaciones.json` (CLI `python3 estado/cola_aplicaciones.py`).
- Pre-filtro: `python3 estado/filtro_vacante.py`.
- CV: `recursos/cv/base-isaac-urdaneta.md`, `recursos/guias/cv-reglas-ats.md`; outputs en `resultados/cv/`.
- Estado: `estado/historial.json`, `estado/orquestador.py`.

## Fases

1. **Poblar cola (dedup)**
   - Leer bloque Wellfound, extraer título, empresa, ubicación, seniority, URL.
   - Deduplicar por URL frente a lo ya en cola y frente a historial.
   - Filtrar relevantes (contienen `flutter|dart|mobile|android|ios`). Reportar cuántos quedan.

2. **Loop uno por uno**
   Para cada elemento `pendiente/evaluando` con cupo (`APLICACION_MAX_DIA`, default 5 aplicados/hoy):
   
   a. **Traer descripción** — `webfetch` a la URL de Wellfound. Guardar texto en `/tmp/wf-<id>.txt`. (Si el HTML es muy dinámico, avisar y proponer navegador asistido.)
   
   b. **Pre-filtro** — `python3 estado/filtro_vacante.py --titulo "<t>" --empresa "<e>" --archivo /tmp/wf-<id>.txt`. 
     - Si **FAIL**: marcar `descartado` (con hallazgos), pasar al siguiente.
     - Si **PASS/avisos**: continuar.
   
   c. **Fase 2 (vale la pena)** — aplicar regla cv-apply (Flutter core ≥60%). 
     - Si **NO**: mostrar score+gaps, preguntar: **descartar / generar igual / saltar**. Ejecutar.
     - Si **SÍ**: avanzar.
   
   d. **Generar CV** — invocar lógica de `cv-apply` (Fase 3–5): CV + carta + PDF en español/inglés según vacante. Guardar rutas en cola. Marcar `cv_listo`.
   
   e. **Presentar paquete (validación obligatoria)** — mostrar: título/empresa/link, rutas .md/.pdf, carta (resumida), pre-filtro/avisos. Opciones: **ok / modificar / saltar / parar**. 
     - `modificar`: permitir ajustar carta/resumen (actualizar archivos y cola).
     - `saltar`: marcar `saltado`, siguiente.
     - `parar`: terminar ronda.
   
   f. **Aplicar** — **modo asistido (recomendado)**: abrir navegador con sesión ya logueada (Wellfound requiere login), navegar a URL, rellenar con paquete (pegar carta/CV donde proceda), **pausar para que tú pulses "Apply"**. Solo tras confirmar "aplicado con éxito" en ese paso, marcar `aplicado` en cola y `vacantes "<key>" applied` (crea seguimiento D+7). **Nunca** intentar evadir protecciones ni automatizar envío completo.

3. **Reporte final**: estadísticas (pendientes/descartados/cv_listo/aplicados/hoy), URLs con estado.

## Decisiones
- **A) Asistido con pausa** (obligatorio): cumplimos regla anti-bot (sin automatizar sesión/autocompletado agresivo o bypass). El usuario confirma el envío efectivo.
- **Ritmo**: `APLICACION_MAX_DIA=5` (configurable). Cupo respetado.
- **Solo relevantes**: por defecto solo títulos con flutter/dart/mobile/android/ios.
- **Intern/Junior**: no se saltan automáticamente; se muestran con F8 y el usuario decide.

## Notas
- Wellfound es SSR, por lo que la descripción suele obtenerse con webfetch + UA completo.
- Algunas vacantes redirigen a ATS externo (Greenhouse/Lever/Workday): el navegador asistido maneja ese caso.
- Nunca modifica archivos base (`recursos/cv/*`).
