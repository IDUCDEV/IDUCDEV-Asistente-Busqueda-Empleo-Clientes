#!/usr/bin/env python3
"""Tests de estado/tracker.py (el "cerebro": historial, dedup, estados)."""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tracker import (CATEGORIES, Historial, domain_key, normalize_company,
                     normalize_title, vacancy_key)  # noqa: E402

ISO = "%Y-%m-%dT%H:%M:%S%z"
WEEK_AGO = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")


class TestNormalize(unittest.TestCase):
    def test_company_limpia_sufijos_y_simbolos(self):
        self.assertEqual(normalize_company("ACME, Inc."), "acme")
        self.assertEqual(normalize_company("Foo S.A."), "foo sa")
        self.assertEqual(normalize_company("") , "")

    def test_title_normalizado(self):
        self.assertEqual(normalize_title("Flutter  Developer!"), "flutter developer")

    def test_vacancy_key(self):
        self.assertEqual(
            vacancy_key("ACME, Inc.", "Senior Flutter Dev!"),
            "acme::senior flutter dev",
        )

    def test_domain_key(self):
        self.assertEqual(domain_key("https://www.sub.empresa.com/"), "empresa.com")
        self.assertEqual(domain_key(""), "")


class TestHistorial(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hist-test-")
        self.path = os.path.join(self.tmp, "historial.json")
        self.h = Historial(path=self.path)

    def test_add_devuelve_true_solo_la_primera_vez(self):
        self.assertTrue(self.h.add("vacantes", "empresa::puesto", {"url": "x"}))
        self.assertFalse(self.h.add("vacantes", "empresa::puesto", {"url": "y"}))
        self.assertFalse(self.h.add("vacantes", "empresa::puesto"))
        self.assertTrue(self.h.is_known("vacantes", "empresa::puesto"))

    def test_add_persiste_en_disco(self):
        self.h.add("vacantes", "empresa::puesto")
        h2 = Historial(path=self.path)
        self.assertTrue(h2.is_known("vacantes", "empresa::puesto"))

    def test_meta_actualiza_item_existente(self):
        self.h.add("vacantes", "empresa::puesto", {"url": "old"})
        self.h.add("vacantes", "empresa::puesto", {"url": "new"})
        self.assertEqual(self.h.get("vacantes", "empresa::puesto")["url"], "new")

    def test_set_state_actualiza(self):
        self.h.add("vacantes", "empresa::puesto")
        self.assertTrue(self.h.set_state("vacantes", "empresa::puesto", "applied"))
        item = self.h.get("vacantes", "empresa::puesto")
        self.assertEqual(item["estado"], "applied")
        self.assertIn("fecha_actualizado", item)
        self.assertFalse(self.h.set_state("vacantes", "no existe", "applied"))

    def test_by_state_filtra(self):
        self.h.add("vacantes", "a::x")
        self.h.add("vacantes", "b::y")
        self.h.set_state("vacantes", "b::y", "descartado")
        self.assertEqual(len(self.h.by_state("vacantes", ("nuevo",))), 1)
        self.assertEqual(len(self.h.by_state("vacantes")), 2)

    def test_pendientes_agrupa(self):
        self.h.add("vacantes", "a::x")
        pen = self.h.pendientes()
        self.assertIn("vacantes", pen)
        self.assertEqual(len(pen["vacantes"]), 1)

    def test_vencidos_detecta_items_sin_actualizar(self):
        self.h.add("proyectos_workana", "slug-ejemplo")
        self.h.set_state("proyectos_workana", "slug-ejemplo", "applied")
        # forzar fecha vieja
        item = self.h.get("proyectos_workana", "slug-ejemplo")
        item["fecha_actualizado"] = WEEK_AGO
        self.h.save()
        vencidos = self.h.vencidos(3)
        self.assertEqual(len(vencidos), 1)
        self.assertEqual(vencidos[0]["categoria"], "proyectos_workana")

    def test_vencidos_ignora_items_recientes(self):
        self.h.add("vacantes", "a::x")
        self.h.set_state("vacantes", "a::x", "applied")
        self.assertEqual(self.h.vencidos(3), [])

    def test_stats_cubre_todas_las_categorias(self):
        stats = self.h.stats()
        for cat in CATEGORIES:
            self.assertIn(cat, stats)

    def test_categoria_vacantes_empresa_para_tableros_ats(self):
        # Vacantes halladas en tableros de empresa (flutter-employers) usan
        # "empresa::titulo" para poder deduplicar contra las de los agregadores.
        self.assertIn("vacantes_empresa", CATEGORIES)
        h = Historial(path=os.path.join(self.tmp, "otro.json"))
        self.assertTrue(h.add("vacantes_empresa",
                              vacancy_key("Canonical", "Flutter Web Frontend Engineer")))
        # La clave es empresa::título (sin URL), así que la misma vacante
        # reaparecida en otro agregador no se vuelve a listar.
        self.assertFalse(h.add("vacantes_empresa",
                               vacancy_key("Canonical", "Flutter Web Frontend Engineer")))
        # Otra vacante de la misma empresa sí es nueva.
        self.assertTrue(h.add("vacantes_empresa",
                              vacancy_key("Canonical", "Mobile Engineer (Flutter)")))
        self.assertEqual(len(h.by_state("vacantes_empresa", "nuevo")), 2)


if __name__ == "__main__":
    unittest.main()