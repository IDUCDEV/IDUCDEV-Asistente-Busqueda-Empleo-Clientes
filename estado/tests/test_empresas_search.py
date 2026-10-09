#!/usr/bin/env python3
"""Tests de .opencode/skills/flutter-employers/empresas_search.py (motor de tableros ATS).

Sin red: estos casos fijan las tres trampas reales que seotonicen durante el
trabajo con tableros, más el bug de presupuesto que hacía que una ronda de 60
empresas solo sondeara ~6.

No hacen red: todo lo que necesitason se simula con monkeypatching de http_get /
http_post_json.
"""

import os
import sys
import unittest

# .../<proyecto>/estado/tests/ → RAIZ = <proyecto>
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "estado"))
sys.path.insert(0, os.path.join(RAIZ, ".opencode", "skills", "flutter-employers"))

import empresas_search as es  # noqa: E402


class TestFechas(unittest.TestCase):
    def test_lever_epoch_en_segundos(self):
        self.assertEqual(es.to_iso_date(1790040082), "2026-09-22")

    def test_lever_epoch_en_milisegundos(self):
        self.assertEqual(es.to_iso_date(1790040082000), "2026-09-22")

    def test_iso_pasa_tal_cual(self):
        self.assertEqual(es.to_iso_date("2026-10-01T10:00:00Z"), "2026-10-01")

    def test_workday_relativas(self):
        # El listado CXS no manda ISO, manda "Posted 13 Days Ago".
        self.assertEqual(es.parse_relative_date("Posted 13 Days Ago"), "2026-09-22")
        self.assertEqual(es.parse_relative_date("Posted Today"), "2026-10-05")

    def test_workday_relativas_con_signo_mas(self):
        # "Posted 30+ Days Ago": el "+" rompe un \\d+\\s*([a-z]+) ingenuo.
        self.assertEqual(es.parse_relative_date("Posted 30+ Days Ago"), "2026-09-05")

    def test_workday_meses_y_anos(self):
        self.assertEqual(es.parse_relative_date("Posted 2 Months Ago"), "2026-08-06")
        self.assertEqual(es.parse_relative_date("Posted 1 Year Ago"), "2025-10-05")

    def test_fecha_ilegible_no_inventa(self):
        self.assertEqual(es.parse_relative_date("nonsense"), "")
        self.assertEqual(es.to_iso_date(""), "")


class TestUrlWorkday(unittest.TestCase):
    def test_el_path_cxs_no_lleva_locale(self):
        # "wday/cxs/rappi/es/Rappi_jobs" responde 405 en tableros reales;
        # el site es "Rappi_jobs" pelado.
        site, locale = es.workday_site("es/Rappi_jobs")
        self.assertEqual((site, locale), ("Rappi_jobs", "es"))

    def test_site_sin_locale(self):
        self.assertEqual(es.workday_site("Rappi_jobs"), ("Rappi_jobs", ""))

    def test_tenant_no_es_el_subdominio_numerico(self):
        # nvidia.wd5 → tenant "nvidia"; rappi.wd12 → tenant "rappi".
        self.assertEqual(es.workday_tenants("nvidia.wd5.myworkdayjobs.com"), ["nvidia"])
        self.assertEqual(es.workday_tenants("rappi.wd12.myworkdayjobs.com"), ["rappi"])

    def test_tenants_descarta_el_dominio(self):
        # Sin esto devolvía ['rappi','myworkdayjobs','com'] y probaba 3 URLs de
        # gusto por empresa.
        self.assertEqual(es.workday_tenants("wd3.myworkdayjobs.com"), ["wd3"])
        self.assertEqual(es.workday_tenants("myworkdayjobs.com"), [])

    def test_url_cxs_armada(self):
        self.assertEqual(
            es.workday_cxs_url("rappi.wd12.myworkdayjobs.com", "rappi", "Rappi_jobs"),
            "https://rappi.wd12.myworkdayjobs.com/wday/cxs/rappi/Rappi_jobs/jobs")


class TestHuellaWorkday(unittest.TestCase):
    def test_codifica_host_y_slug(self):
        pat = dict(es.ATS_FINGERPRINTS)["workday"]
        m = pat.search('<a href="https://rappi.wd12.myworkdayjobs.com/es/Rappi_jobs">')
        self.assertIsNotNone(m)
        host, locale, site = m.group(1), m.group(2), m.group(3)
        self.assertEqual(host, "rappi.wd12.myworkdayjobs.com")
        self.assertEqual(locale, "es/")
        self.assertEqual(site, "Rappi_jobs")
        # El formato que consume el Prober: ats="workday:<host>", slug="<locale><site>".
        self.assertEqual(f"workday:{host.lower()}", "workday:rappi.wd12.myworkdayjobs.com")
        self.assertEqual(f"{locale}{site}", "es/Rappi_jobs")

    def test_descarta_site_generico(self):
        pat = dict(es.ATS_FINGERPRINTS)["workday"]
        m = pat.search('<a href="https://x.wd1.myworkdayjobs.com/en/index">')
        self.assertIsNotNone(m)
        self.assertEqual(m.group(3).lower(), "index")


class TestNormWorkday(unittest.TestCase):
    PAYLOAD = {
        "total": 2,
        "jobPostings": [
            {"title": "Mobile Engineer", "externalPath": "/job/CO-Bogota/Mobile-JR1",
             "locationsText": "Colombia, Bogota", "postedOn": "Posted 13 Days Ago",
             "bulletFields": ["JR1"]},
            {"title": "Flutter Dev", "externalPath": "/job/Remote/Flutter-JR2",
             "locationsText": "Remote", "postedOn": "Posted Today", "bulletFields": ["JR2"]},
        ],
    }

    def test_normaliza_los_campos(self):
        roles = es.norm_workday(self.PAYLOAD, "acme.wd1.myworkdayjobs.com",
                                "es/Acme_jobs")
        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0]["title"], "Mobile Engineer")
        self.assertEqual(roles[0]["location"], "Colombia, Bogota")
        self.assertEqual(roles[0]["published"], "2026-09-22")
        self.assertEqual(roles[0]["ref"], "JR1")

    def test_url_de_aplicacion_lleva_locale(self):
        # El path CXS va sin locale, pero el de navegación (el que aplica el
        # usuario) sí. Si se mezclan, la URL del informe da 404.
        roles = es.norm_workday(self.PAYLOAD, "acme.wd1.myworkdayjobs.com",
                                "es/Acme_jobs")
        self.assertEqual(
            roles[0]["url"],
            "https://acme.wd1.myworkdayjobs.com/es/Acme_jobs/job/CO-Bogota/Mobile-JR1")

    def test_matched_refleja_el_termino(self):
        roles = es.norm_workday(self.PAYLOAD, "h", "es/S", matched="dart")
        self.assertEqual(roles[0]["matched"], "dart")


class TestFiltroStack(unittest.TestCase):
    def test_titulo_con_flutter_gana(self):
        sel = es.select_roles([{"title": "Flutter Developer", "location": "Remote"}], {})
        self.assertEqual(len(sel), 1)
        self.assertFalse(sel[0]["review"])

    def test_mobile_con_flutter_en_descripcion_a_revision(self):
        sel = es.select_roles([{"title": "Mobile Engineer",
                                "location": "Remote",
                                "description": "you will use Flutter and Dart"}], {})
        self.assertEqual(len(sel), 1)
        self.assertTrue(sel[0]["review"])

    def test_matched_flutter_confirma_aunque_el_titulo_no_lo_diga(self):
        # Un "Mobile Engineer" encontrado por searchText=flutter SÍ es Flutter:
        # el listado CXS no trae descripción, pero el board laconfirmó.
        sel = es.select_roles([{"title": "Mobile Engineer", "location": "Remote",
                                "matched": "flutter"}], {})
        self.assertEqual(len(sel), 1)
        self.assertFalse(sel[0]["review"])

    def test_matched_no_flutter_no_confirma(self):
        # "mobile" no es Flutter: no debe colarse por la puerta de atrás.
        sel = es.select_roles([{"title": "Mobile Engineer", "location": "Remote",
                                "matched": "mobile"}], {})
        self.assertEqual(sel, [])

    def test_descarta_stack_distinto(self):
        sel = es.select_roles([{"title": "Backend Python", "location": "Remote"}], {})
        self.assertEqual(sel, [])


class TestAplicabilidad(unittest.TestCase):
    def test_presencial_fuera_de_latam_se_descarta(self):
        self.assertFalse(es.es_aplicable(
            {"title": "Sr Manager", "location": "India, Pune"}, {}))

    def test_remoto_pasa_aunque_el_pais_no_sea_latam(self):
        self.assertTrue(es.es_aplicable(
            {"title": "Sr Flutter", "location": "India, Pune",
             "description": "Remote"}, {}))

    def test_latam_pasa(self):
        self.assertTrue(es.es_aplicable(
            {"title": "Flutter", "location": "Mexico City"}, {}))

    def test_sin_datos_no_se_descarta(self):
        # Ante la duda se conserva: preferimos un falso positivo a perder una
        # vacante real.
        self.assertTrue(es.es_aplicable({"title": "Flutter", "location": ""}, {}))

    def test_este_espacio_no_se_descarta(self):
        self.assertTrue(es.es_aplicable(
            {"title": "Flutter", "location": "US, CA, Santa Clara"}, {}))


class TestPresupuestoPorEmpresa(unittest.TestCase):
    """Regresión del bug que hacía la ronda casi inútil."""

    def setUp(self):
        self._get, self._sleep = es.http_get, es.time.sleep
        es.http_get = lambda url, timeout=None: "__404__"  # todo 404
        es.time.sleep = lambda s: None  # los pausas harían el test tardar 2+ min
        self.addCleanup(lambda: (setattr(es, "http_get", self._get),
                                 setattr(es, "time.sleep", self._sleep)))

    def test_presupuesto_se_reinicia_entre_empresas(self):
        p = es.Prober(slug_ciegos=True)
        for i in range(30):
            p.probe({"name": f"Empresa{i}", "domain": f"e{i}.com"})
        # Con el bug, self.intentos era GLOBAL: al llegar a MAX_INTENTOS (10),
        # todas las empresas siguientes devolvían (None,None,[]) sin hacer una
        # sola petición. En una ronda de 60 empresas solo se sondeaban ~6.
        self.assertEqual(p.intentos, 30 * es.Prober.MAX_INTENTOS)
        self.assertEqual(p.fallos, 0)

    def test_ultima_empresa_tambien_se_sondea(self):
        p = es.Prober(slug_ciegos=True)
        for i in range(30):
            p.probe({"name": f"Empresa{i}", "domain": f"e{i}.com"})
        self.assertLessEqual(p._usados, es.Prober.MAX_INTENTOS)
        self.assertGreater(p.intentos, 29 * es.Prober.MAX_INTENTOS)

    def test_slugs_ciegos_desactivado_por_defecto(self):
        # Medido: rinde ~0% en LATAM y cuesta ~10 peticiones por empresa. El
        # default rápido es leer la página de carreras y nada más.
        self.assertFalse(es.Prober().slug_ciegos)
        p = es.Prober()
        for i in range(30):
            p.probe({"name": f"Empresa{i}", "domain": f"e{i}.com"})
        self.assertEqual(p.intentos, 30, "una sola petición: la de leer /careers")

    def test_get_no_contabiliza_host_muerto_como_fallo(self):
        # Un subdominio retirado (p. ej. wd12.myworkdayjobs.com) no es "el sitio
        # nos bloquea": si contara, dispararía el cortocircuito y pararía la ronda.
        es.http_get = lambda url, timeout=None: "__NET__"
        p = es.Prober()
        p.probe({"name": "Muerta", "domain": "muerta.com"})
        self.assertEqual(p.fallos, 0)

    def test_resolve_board_corta_en_el_dominio_muerto(self):
        # Si el dominio no resuelve, /jobs y /vacantes tampoco: probar las 5 rutas
        # es gastar 5 timeouts para nada. Solo pide la primera.
        pedidas = []

        def fake_get(url, timeout=None):
            pedidas.append(url)
            return "__NET__"

        self._get = es.http_get
        es.http_get = fake_get
        self.addCleanup(lambda: setattr(es, "http_get", self._get))

        ats, slug, url = es.resolve_board({"name": "Muerta", "domain": "muerta.com"})
        self.assertEqual((ats, slug, url), (None, None, None))
        self.assertEqual(len(pedidas), 1, "no debe probar más rutas de un dominio muerto")

    def test_resolve_board_sigue_probando_si_la_ruta_no_existe(self):
        # Un 404 en /careries es lo normal: la empresa puede tener /jobs. Solo
        # el __NET__ (no resuelve) corta la búsqueda.
        cuerpo = '<a href="https://boards.greenhouse.io/miemapresa">Jobs</a>'

        def fake_get(url, timeout=None):
            return "__404__" if url.endswith("/careers") else cuerpo

        self._get = es.http_get
        es.http_get = fake_get
        self.addCleanup(lambda: setattr(es, "http_get", self._get))

        ats, slug, _ = es.resolve_board({"name": "Acme", "domain": "acme.com"})
        self.assertEqual(ats, "greenhouse")
        self.assertEqual(slug, "miemapresa")


class TestProcedenciaDelTablero(unittest.TestCase):
    """`Prober.resolution` distingue un tablero fiable de uno adivinado.

    Es lo que permite al verificador registrar (y reparar) un tablero vacío que
    salió de la página de la propia empresa, sin meter los ~0% que salen de
    adivinar slugs.
    """

    def setUp(self):
        self._get, self._sleep = es.http_get, es.time.sleep
        es.time.sleep = lambda s: None
        self.addCleanup(lambda: (setattr(es, "http_get", self._get),
                                 setattr(es, "time.sleep", self._sleep)))

    def test_desde_la_pagina_de_carreras_marca_careers(self):
        pagina = '<a href="https://boards.greenhouse.io/acme">Jobs</a>'

        def fake_get(url, timeout=None):
            return "__404__" if url.endswith("/careers") else pagina

        es.http_get = fake_get
        p = es.Prober()
        ats, slug, roles = p.probe({"name": "Acme", "domain": "acme.com"})
        self.assertEqual(p.resolution, "careers")
        self.assertTrue(p.last_careers_url.endswith("/jobs"))

    def test_desde_el_registro_marca_registro(self):
        es.http_get = lambda url, timeout=None: '{"jobs":[{"title":"X"}]}'
        p = es.Prober()
        p.probe({"name": "Acme", "domain": "acme.com",
                 "ats": "greenhouse", "slug": "acme"})
        self.assertEqual(p.resolution, "registro")

    def test_slug_adivinado_marca_ciego(self):
        es.http_get = lambda url, timeout=None: (
            "__404__" if "/careers" in url else '{"jobs":[{"title":"Dev"}]}')
        p = es.Prober(slug_ciegos=True)
        p.probe({"name": "Acme", "domain": "acme.com"})
        self.assertEqual(p.resolution, "ciego")


class TestFetchWorkdaySimulado(unittest.TestCase):
    def test_prueba_otro_tenant_si_el_primero_falla(self):
        llamadas = []

        def fake_post(url, payload, timeout=None):
            llamadas.append(url)
            if "/wday/cxs/roto/" in url:
                return "__ERR__:405"
            return '{"total":1,"jobPostings":[{"title":"Flutter Dev",' \
                   '"externalPath":"/job/X","locationsText":"Remote"}]}'

        self._post, self._sleep = es.http_post_json, es.time.sleep
        es.http_post_json = fake_post
        es.time.sleep = lambda s: None
        self.addCleanup(lambda: (setattr(es, "http_post_json", self._post),
                                 setattr(es, "time.sleep", self._sleep)))

        # Host con dos etiquetas utilizables: "roto" falla y "bueno" responde.
        # (las etiquetas "wd<N>" nunca son tenant, así que no sirven aquí)
        data = es.workday_fetch("roto.bueno.myworkdayjobs.com", "es/Site_jobs",
                                search="flutter")
        self.assertIsNotNone(data)
        self.assertEqual(len(llamadas), 2, "debe probar el segundo tenant")
        self.assertIn("/wday/cxs/bueno/Site_jobs/jobs", llamadas[-1])


if __name__ == "__main__":
    unittest.main()