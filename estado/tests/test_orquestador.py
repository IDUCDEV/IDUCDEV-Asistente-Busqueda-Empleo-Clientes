#!/usr/bin/env python3
"""Tests de estado/orquestador.py (rondas, tareas, seguimientos, marcar)."""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest.mock  # noqa: E402

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
        oq.HISTORIAL_PATH = self.hist_path
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

    def test_parse_ignora_avisos_de_progreso_como_ruta(self):
        """`[parcial] 20/60` sale antes que la ruta: no puede ser el archivo."""
        out = """[parcial] 20/60 empresas sondeadas
[parcial] 60/60 empresas sondeadas
resultados/empresas-target/2026-10-26-empresas-vacantes.md
---JOBCOUNT---
6
---NUEVAS---
1
---ENCOLADAS---
5
---SKIPPED---
5
"""
        res = oq._parse_script_output(out)
        self.assertEqual(res["path"],
                         "resultados/empresas-target/2026-10-26-empresas-vacantes.md")
        self.assertEqual(res["nuevas"], 1, "NUEVAS manda sobre JOBCOUNT")
        self.assertEqual(res["jobcount"], 6)
        self.assertEqual(res["encoladas"], 5)
        self.assertEqual(res["omitidas"], 5)

    def test_parse_sin_seccion_nuevas_usa_jobcount(self):
        """job-search no emite ---NUEVAS---: JOBCOUNT ya son las nuevas."""
        out = """resultados/vacantes/2026-10-26.md
---JOBCOUNT---
65
---SKIPPED---
80
"""
        res = oq._parse_script_output(out)
        self.assertEqual(res["nuevas"], 65)
        self.assertEqual(res["encoladas"], 0)

    def test_parse_seccion_desconocida_no_contamina_la_ruta(self):
        out = """---STATS---
empresas: 154
"""
        res = oq._parse_script_output(out)
        self.assertIsNone(res["path"])


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

    def test_fase_completada_con_errores_sale_ok_y_avisa(self):
        """Corrió entera pero con fuentes caídas: ok=True y ⚠️ en el informe."""
        oq.registrar_fase("empresas-search", "resultados/empresas-target/x.md",
                          nuevas=1, omitidas=5, errores=["Clip: sin tablero localizado"],
                          ok=True)
        fase = oq.load_rondas()["rondas"][0]["fases"][0]
        self.assertTrue(fase["ok"])
        self.assertEqual(fase["errores"], ["Clip: sin tablero localizado"])
        with open(os.path.join(self.info_dir, f"{oq.today()}-resumen.md"),
                  encoding="utf-8") as fh:
            texto = fh.read()
        self.assertIn("⚠️", texto)
        self.assertNotIn("❌", texto)

    def test_fase_marcada_fallida_sale_fallida(self):
        oq.registrar_fase("job-search", "resultados/vacantes/x.md",
                          errores=["linkedin: timeout"], ok=False)
        self.assertFalse(oq.load_rondas()["rondas"][0]["fases"][0]["ok"])


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


class TestCmdReset(OrquestadorTestCase):
    def test_reset_limpia_dbs_con_yes(self):
        self.tracker.add("vacantes", "empresa::puesto", {"url": "https://x"})
        self.tracker.add("vacantes_empresa", "empresa::puesto ats")
        oq.tarea_nueva("seguimiento_aplicacion", "vacantes", "empresa::puesto",
                       "Seguimiento: empresa::puesto", dias=7)
        oq.registrar_fase("job-search", "resultados/vacantes/2026-09-20.md", nuevas=5)

        self.assertEqual(oq.cmd_reset(SimpleNamespace(yes=True)), 0)

        h = _Historial(path=self.hist_path)
        self.assertEqual(h.stats(), {cat: 0 for cat in _Historial(path=self.hist_path).stats()})
        self.assertEqual(sum(h.stats().values()), 0, "historial debe quedar vacío")
        self.assertEqual(oq.load_tareas(), {"tareas": []})
        self.assertEqual(oq.load_rondas(), {"rondas": []})

    def test_reset_aborta_sin_confirmacion(self):
        self.tracker.add("vacantes", "empresa::puesto", {"url": "https://x"})
        with unittest.mock.patch("builtins.input", return_value="n"):
            self.assertEqual(oq.cmd_reset(SimpleNamespace(yes=False)), 1)
        self.assertEqual(len(_Historial(path=self.hist_path).data["vacantes"]), 1,
                         "sin confirmación no se debe borrar nada")


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