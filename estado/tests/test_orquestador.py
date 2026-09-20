#!/usr/bin/env python3
"""Tests de estado/orquestador.py (rondas, tareas, seguimientos, marcar)."""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import orquestador as oq  # noqa: E402
from tracker import Historial as _Historial  # noqa: E402

WEEK_AGO = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(timespec="seconds")


class OrquestadorTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orq-test-")
        self.hist_path = os.path.join(self.tmp, "historial.json")
        self.tarea_path = os.path.join(self.tmp, "tareas.json")
        self.ronda_path = os.path.join(self.tmp, "rondas.json")
        self.info_dir = os.path.join(self.tmp, "informes")

        # Aislar todas las rutas de las que depende el orquestador
        oq.TAREAS_PATH = self.tarea_path
        oq.RONDAS_PATH = self.ronda_path
        oq.OUTPUT_DIRS = {"informes": self.info_dir}
        oq.Historial = lambda: _Historial(path=self.hist_path)

        self.tracker = _Historial(path=self.hist_path)

    def tearDown(self):
        oq.Historial = _Historial


class TestParseOutput(unittest.TestCase):
    def test_parse_script_output_extrae_secciones(self):
        out = """resultados/vacantes/2026-09-20.md
Posible spam / caducada: 2

---JOBCOUNT---
5
---SKIPPED---
3
---SOURCES---
linkedin: 2
getonboard: 3
---ERRORS---
computrabajo: fallo conexión
"""
        res = oq._parse_script_output(out)
        self.assertEqual(res["path"], "resultados/vacantes/2026-09-20.md")
        self.assertEqual(res["nuevas"], 5)
        self.assertEqual(res["omitidas"], 3)
        self.assertEqual(res["fuentes"], {"linkedin": "2", "getonboard": "3"})
        self.assertEqual(res["errores"], ["computrabajo: fallo conexión"])

    def test_parse_script_output_vacio(self):
        res = oq._parse_script_output("")
        self.assertIsNone(res["path"])
        self.assertEqual(res["nuevas"], 0)


class TestTareas(OrquestadorTestCase):
    def test_tarea_nueva_y_done(self):
        t = oq.tarea_nueva("seguimiento_aplicacion", "vacantes", "empresa::puesto",
                           "Seguimiento: empresa::puesto", dias=7)
        self.assertEqual(t["estado"], "pendiente")
        self.assertIn("t-", t["id"])
        self.assertTrue(oq.tarea_done(t["id"]))
        self.assertEqual(oq.tareas_pendientes(), [])
        self.assertFalse(oq.tarea_done("t-inexistente"))

    def test_tarea_existe_dedup(self):
        oq.tarea_nueva("seguimiento_outreach", "outreach", "U", "x")
        self.assertTrue(oq._tarea_existe("seguimiento_outreach", "U"))
        # tras marcarla hecha, el guard no la considera duplicada
        self.assertTrue(oq.tarea_done(oq.tareas_pendientes()[0]["id"]))
        self.assertFalse(oq._tarea_existe("seguimiento_outreach", "U"))


class TestRondas(OrquestadorTestCase):
    def test_registrar_fase_guarda_y_es_idempotente(self):
        oq.registrar_fase("job-search", "resultados/vacantes/2026-09-20.md",
                          nuevas=5, omitidas=3)
        rondas = oq.load_rondas()
        self.assertEqual(len(rondas["rondas"]), 1)
        fases = rondas["rondas"][0]["fases"]
        self.assertEqual(len(fases), 1)
        self.assertEqual(fases[0]["fase"], "job-search")
        self.assertEqual(fases[0]["nuevas"], 5)

        # re-registrar la misma fase no duplica
        oq.registrar_fase("job-search", "resultados/vacantes/2026-09-20.md",
                          nuevas=6, omitidas=3)
        rondas = oq.load_rondas()
        self.assertEqual(len(rondas["rondas"][0]["fases"]), 1)
        self.assertEqual(rondas["rondas"][0]["fases"][0]["nuevas"], 6)

    def test_registrar_fase_genera_informe(self):
        oq.registrar_fase("job-search", "resultados/vacantes/2026-09-20.md", nuevas=2)
        informe = os.path.join(self.info_dir, f"{oq.today()}-resumen.md")
        self.assertTrue(os.path.exists(informe), "debe generar informe del día")
        with open(informe, encoding="utf-8") as fh:
            self.assertIn("## Fases ejecutadas hoy", fh.read())


class TestCmdMarcar(OrquestadorTestCase):
    def test_marcar_applied_crea_seguimiento(self):
        self.tracker.add("vacantes", "empresa::puesto", {"url": "https://x"})
        args = SimpleNamespace(categoria="vacantes", key="empresa::puesto", estado="applied")
        self.assertEqual(oq.cmd_marcar(args), 0)
        item = _Historial(path=self.hist_path).get("vacantes", "empresa::puesto")
        self.assertEqual(item["estado"], "applied")
        pend = oq.tareas_pendientes()
        self.assertEqual(len(pend), 1)
        self.assertEqual(pend[0]["tipo"], "seguimiento_aplicacion")

    def test_marcar_key_inexistente_falla(self):
        args = SimpleNamespace(categoria="vacantes", key="no existe", estado="applied")
        self.assertEqual(oq.cmd_marcar(args), 1)


class TestSeguimientos(OrquestadorTestCase):
    def test_crear_seguimientos_detecta_items_viejos(self):
        self.tracker.add("outreach", "https://linkedin.com/in/fulano", {"url": "https://linkedin.com/in/fulano"})
        self.tracker.set_state("outreach", "https://linkedin.com/in/fulano", "enviado")
        item = self.tracker.get("outreach", "https://linkedin.com/in/fulano")
        item["fecha_actualizado"] = WEEK_AGO
        self.tracker.save()

        self.tracker.add("vacantes", "empresa::puesto")
        self.tracker.set_state("vacantes", "empresa::puesto", "applied")
        item = self.tracker.get("vacantes", "empresa::puesto")
        item["fecha_actualizado"] = WEEK_AGO
        self.tracker.save()

        creados = oq.crear_seguimientos()
        self.assertEqual(creados, 2)
        tipos = {t["tipo"] for t in oq.tareas_pendientes()}
        self.assertEqual(tipos, {"seguimiento_outreach", "seguimiento_aplicacion"})


class TestCmdRonda(OrquestadorTestCase):
    def test_cmd_ronda_registra_fases(self):
        def fake_run(nombre, script):
            res = {"path": f"out/{nombre}.md", "nuevas": 4, "omitidas": 1,
                   "fuentes": {"linkedin": "2"}, "errores": []}
            return res, None

        oq._run_script = fake_run
        args = SimpleNamespace(empleos=True, clientes=False)
        self.assertEqual(oq.cmd_ronda(args), 0)
        rondas = oq.load_rondas()
        fases = {f["fase"] for f in rondas["rondas"][0]["fases"]}
        self.assertTrue(fases)


if __name__ == "__main__":
    unittest.main()