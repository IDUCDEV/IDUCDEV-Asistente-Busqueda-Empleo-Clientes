# /nuevo — Registrar manualmente un item nuevo en el historial

Útil cuando el usuario encuentra un empleo/cliente/contacto fuera del
asistente y quiere que quede en la memoria central (para no repetirlo).

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "estado")
from tracker import Historial
h = Historial()
h.add("vacantes", "<empresa::titulo>", meta={"empresa": "...", "titulo": "...", "url": "...", "fuente": "manual"})
EOF
```

Categorías válidas: `vacantes`, `empresas`, `clientes`, `proyectos_workana`,
`posts_linkedin`, `outreach`. Claves normalizadas (minúsculas).