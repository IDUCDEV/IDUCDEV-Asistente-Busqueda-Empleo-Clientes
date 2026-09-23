# /enviar — Envía los mensajes de venta encolados (uno por uno)

Carga la skill `enviar-clientes` y procesa la cola
(`estado/cola_envios.json`) **uno por uno**, validando cada mensaje con el
usuario antes de enviarlo. No hay modo lote.

Flujo (ronda por-uno):

1. Ver cola y cupo del día:
   ```bash
   python3 estado/cola_envios.py pendientes
   python3 estado/cola_envios.py enviados-hoy
   ```
2. Muestra la tabla de pendientes y pide confirmación para empezar.
   Autorización de navegador si hay WhatsApp/LinkedIn en la cola.
3. **Loop uno por uno** — por cada lead, en orden de la cola (mientras
   haya cupo):
   ```bash
   python3 estado/cola_envios.py ver <id>      # mostrar el mensaje completo
   ```
   Y pregunta: **OK / modificar / saltar / parar**.
   - OK → enviar por canal (pausa 15-35s entre WhatsApp; límite diario
     `ENVIO_MAX_DIA`, default 12):
     - email → `python3 estado/enviar_email.py --id <id>`
     - whatsapp → WhatsApp Web con link `?phone=&text=` + Enter
     - linkedin → pega el mensaje, **tú pulsas Enter**
   - modificar → editar el `.md` + `cola_envios.py editar <id>` →
     mostrar de nuevo → reconfirmar → enviar
   - saltar → queda pendiente para la próxima ronda (sin marcar nada)
   - parar → terminar la ronda, el resto queda pendiente
4. Por cada envío OK:
   ```bash
   python3 estado/cola_envios.py marcar <id> enviado
   python3 estado/orquestador.py marcar clientes "<clave>" contactado
   ```
5. Registra la fase y regenera el informe.

Atajos: `/enviar solo email`, `/enviar sin navegador` (solo email; el resto
queda pendiente).