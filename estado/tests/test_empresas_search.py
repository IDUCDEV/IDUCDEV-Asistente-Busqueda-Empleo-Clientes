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
from datetime import datetime, timedelta, timezone

# .../<proyecto>/estado/tests/ → RAIZ = <proyecto>
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "estado"))
sys.path.insert(0, os.path.join(RAIZ, ".opencode", "skills", "flutter-employers"))

import empresas_search as es  # noqa: E402


def hace(dias):
    """Fecha YYYY-MM-DD de hace N días: los tests de fechas no deben caducar."""
    return (datetime.now(timezone.utc) - timedelta(days=dias)).date().isoformat()


class TestFechas(unittest.TestCase):
    def test_lever_epoch_en_segundos(self):
        self.assertEqual(es.to_iso_date(1790040082), "2026-09-22")

    def test_lever_epoch_en_milisegundos(self):
        self.assertEqual(es.to_iso_date(1790040082000), "2026-09-22")

    def test_iso_pasa_tal_cual(self):
        self.assertEqual(es.to_iso_date("2026-10-01T10:00:00Z"), "2026-10-01")

    def test_workday_relativas(self):
        # El listado CXS no manda ISO, manda "Posted 13 Days Ago".
        self.assertEqual(es.parse_relative_date("Posted 13 Days Ago"), hace(13))
        self.assertEqual(es.parse_relative_date("Posted Today"), hace(0))

    def test_workday_relativas_con_signo_mas(self):
        # "Posted 30+ Days Ago": el "+" rompe un \\d+\\s*([a-z]+) ingenuo.
        self.assertEqual(es.parse_relative_date("Posted 30+ Days Ago"), hace(30))

    def test_workday_meses_y_anos(self):
        self.assertEqual(es.parse_relative_date("Posted 2 Months Ago"), hace(60))
        self.assertEqual(es.parse_relative_date("Posted 1 Year Ago"), hace(365))

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
        self.assertEqual(roles[0]["published"], hace(13))
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
        # default rápido es leer la página de carreras (y, si falla, probar el
        # host natural del ATS, que es otra cosa).
        self.assertFalse(es.Prober().slug_ciegos)
        self.assertTrue(es.Prober().host_directo)
        p = es.Prober(host_directo=False)
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
        p = es.Prober(slug_ciegos=True, host_directo=False)
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


class TestHuellasNuevosATS(unittest.TestCase):
    """Los ATS de subdominio son los que faltaban en LATAM/EU."""

    def _detect(self, html, url="https://acme.com/careers"):
        return es.discover_ats(url, raw=html)

    def test_workable(self):
        self.assertEqual(
            self._detect('<a href="https://apply.workable.com/acme">Jobs</a>'),
            ("workable", "acme"))

    def test_recruitee(self):
        self.assertEqual(
            self._detect('<iframe src="https://acme.recruitee.com/o/flutter">'),
            ("recruitee", "acme"))

    def test_teamtailor_con_subdominio(self):
        self.assertEqual(
            self._detect('<a href="https://acme.teamtailor.com/jobs">Jobs</a>'),
            ("teamtailor", "acme.teamtailor.com"))

    def test_teamtailor_en_dominio_propio(self):
        self.assertEqual(
            self._detect('<script src="https://teamtailor-cdn.com/x.js"></script>',
                         "https://jobs.acme.com/jobs"),
            ("teamtailor", "jobs.acme.com"))

    def test_smartrecruiters_bamboohr_personio(self):
        self.assertEqual(
            self._detect('<a href="https://careers.smartrecruiters.com/Acme">'),
            ("smartrecruiters", "acme"))
        self.assertEqual(
            self._detect('<a href="https://acme.bamboohr.com/careers">'),
            ("bamboohr", "acme"))
        self.assertEqual(
            self._detect('<a href="https://acme.jobs.personio.de/xml">'),
            ("personio", "acme"))


class TestNormalizadoresNuevosATS(unittest.TestCase):
    def test_workable(self):
        roles = es.norm_workable({"jobs": [{
            "title": "Flutter Developer", "city": "Bogotá", "country": "Colombia",
            "application_url": "https://apply.workable.com/j/X/apply",
            "description": "<p>Dart</p>", "published_on": "2026-10-15"}]})
        self.assertEqual(roles[0]["title"], "Flutter Developer")
        self.assertEqual(roles[0]["location"], "Bogotá, Colombia")
        self.assertEqual(roles[0]["description"], "Dart")
        self.assertEqual(roles[0]["published"], "2026-10-15")
        self.assertTrue(roles[0]["url"].endswith("/apply"))

    def test_recruitee_marca_remoto(self):
        roles = es.norm_recruitee({"offers": [{
            "title": "Flutter Dev", "location": "LATAM", "remote": True,
            "careers_url": "https://acme.recruitee.com/o/flutter",
            "description": "<p>Dart</p>", "published_at": "2026-10-20 13:51:20 UTC"}]})
        self.assertEqual(roles[0]["location"], "LATAM (Remote)")
        self.assertEqual(roles[0]["published"], "2026-10-20")

    def test_teamtailor_desde_json_feed(self):
        roles = es.norm_teamtailor({"items": [{
            "title": "Flutter Dev", "url": "https://jobs.acme.com/jobs/1",
            "date_published": "2026-10-08T09:01:26+02:00",
            "content_text": "Flutter and Dart",
            "_jobposting": {"jobLocation": {"address": {
                "addressLocality": "Madrid", "addressCountry": "ES"}}}}]})
        self.assertEqual(roles[0]["location"], "Madrid, ES")
        self.assertEqual(roles[0]["published"], "2026-10-08")
        self.assertIn("Flutter", roles[0]["description"])

    def test_smartrecruiters(self):
        roles = es.norm_smartrecruiters({"content": [{
            "id": "123", "name": "Flutter Dev",
            "releasedDate": "2026-10-23T09:43:20.087Z",
            "location": {"fullLocation": "Colombia, Remote"},
            "company": {"identifier": "Acme"}}]})
        self.assertEqual(roles[0]["location"], "Colombia, Remote")
        self.assertEqual(roles[0]["url"],
                         "https://jobs.smartrecruiters.com/Acme/123")

    def test_bamboohr(self):
        roles = es.norm_bamboohr({"result": [{
            "id": "63", "jobOpeningName": "Flutter Developer",
            "location": {"city": "Bogotá", "state": "Cundinamarca"},
            "locationType": "1"}]}, slug="acme")
        self.assertEqual(roles[0]["location"], "Bogotá, Cundinamarca (Remote)")
        self.assertEqual(roles[0]["url"], "https://acme.bamboohr.com/careers/63")

    def test_personio_xml(self):
        xml = ("<workzag-jobs><position><id>9</id><office>Madrid</office>"
               "<name>Flutter Dev</name><createdAt>2026-10-01</createdAt>"
               "<jobDescriptions><jobDescription><name>D</name>"
               "<value><![CDATA[<p>Dart</p>]]></value></jobDescription>"
               "</jobDescriptions></position></workzag-jobs>")
        roles = es.norm_personio(xml, slug="acme")
        self.assertEqual(roles[0]["title"], "Flutter Dev")
        self.assertEqual(roles[0]["url"], "https://acme.jobs.personio.de/job/9")
        self.assertEqual(roles[0]["description"], "Dart")

    def test_personio_prueba_los_dos_dominios(self):
        self.assertEqual(len(es.board_urls("personio", "acme")), 2)


class TestHostDirecto(unittest.TestCase):
    def setUp(self):
        self._get = es.http_get
        self.addCleanup(lambda: setattr(es, "http_get", self._get))

    def test_slugs_por_dominio_y_nombre(self):
        self.assertEqual(
            es.host_slugs({"name": "Somnio Software", "domain": "somniosoftware.com"}),
            ["somniosoftware"])
        self.assertEqual(
            es.host_slugs({"name": "Senior Sistemas", "domain": "senior.com.br"}),
            ["senior", "seniorsistemas"])

    def test_encuentra_recruitee_aunque_careers_sea_una_spa(self):
        def fake_get(url, timeout=None):
            if "recruitee.com" in url:
                return es.json.dumps({"offers": [{
                    "title": "Flutter Developer", "careers_url": "https://x/1",
                    "location": "LATAM", "description": "Dart",
                    "published_at": "2026-10-20 13:51:20 UTC"}]})
            if "/careers" in url or "/jobs" in url:
                return "<html><body>SPA sin enlaces al ATS</body></html>"
            return "__404__"

        es.http_get = fake_get
        p = es.Prober()
        ats, slug, roles = p.probe(
            {"name": "Somnio Software", "domain": "somniosoftware.com"})
        self.assertEqual((ats, slug), ("recruitee", "somniosoftware"))
        self.assertEqual(p.resolution, "host-directo")
        self.assertEqual(len(roles), 1)

    def test_no_registra_tablero_vacio_de_smartrecruiters(self):
        def fake_get(url, timeout=None):
            if "smartrecruiters.com" in url:
                return es.json.dumps({"content": [], "totalFound": 0})
            return "__404__"

        es.http_get = fake_get
        p = es.Prober()
        ats, _, _ = p.probe({"name": "Acme", "domain": "acme.com"})
        self.assertIsNone(ats)

    def test_encuentra_greenhouse_con_el_slug_del_dominio(self):
        """QuintoAndar: 110 vacantes en Greenhouse y su web no enlaza el tablero."""
        def fake_get(url, timeout=None):
            if url == "https://boards-api.greenhouse.io/v1/boards/quintoandar":
                return es.json.dumps({"name": "QuintoAndar"})
            if url.startswith("https://boards-api.greenhouse.io/v1/boards/quintoandar/"):
                return es.json.dumps({"jobs": [{
                    "title": "Pessoa Desenvolvedora Mobile", "id": 1,
                    "absolute_url": "https://boards.greenhouse.io/quintoandar/jobs/1",
                    "location": {"name": "Brazil"}, "updated_at": "2026-10-20",
                    "content": "Flutter e Dart"}]})
            if "/careers" in url or "/jobs" in url or "/vacantes" in url:
                return "<html><body>SPA</body></html>"
            return "__404__"

        es.http_get = fake_get
        p = es.Prober()
        ats, slug, roles = p.probe(
            {"name": "QuintoAndar", "domain": "quintoandar.com.br"})
        self.assertEqual((ats, slug), ("greenhouse", "quintoandar"))
        self.assertEqual(p.resolution, "host-directo")
        self.assertEqual(len(roles), 1)

    def test_descarta_tablero_global_de_otra_empresa(self):
        """Slug genérico: el board existe pero es de un tercero homónimo."""
        def fake_get(url, timeout=None):
            if url == "https://boards-api.greenhouse.io/v1/boards/rows":
                return es.json.dumps({"name": "Rows Financial"})
            if url.startswith("https://boards-api.greenhouse.io/v1/boards/rows/"):
                return es.json.dumps({"jobs": [{
                    "title": "Senior Flutter Developer", "id": 9,
                    "absolute_url": "https://boards.greenhouse.io/rows/jobs/9",
                    "location": {"name": "Remote"}, "updated_at": "2026-10-20",
                    "content": "Flutter"}]})
            return "__404__"

        es.http_get = fake_get
        p = es.Prober()
        ats, _, _ = p.probe({"name": "Rows", "domain": "rows.com"})
        self.assertIsNone(ats)


class TestIdentidadDelTablero(unittest.TestCase):
    def test_acepta_el_mismo_nombre_o_con_sufijo_corporativo(self):
        self.assertTrue(es.board_matches_company("QuintoAndar", "QuintoAndar"))
        self.assertTrue(es.board_matches_company("Somnio", "Somnio Software"))
        self.assertTrue(es.board_matches_company("Acme", "Acme"))

    def test_descarta_una_marca_con_palabra_extra(self):
        self.assertFalse(es.board_matches_company("Rows Financial", "Rows"))
        self.assertFalse(es.board_matches_company("Acme", "Acme Health"))

    def test_sin_datos_no_descarta(self):
        self.assertTrue(es.board_matches_company("", "Acme"))


class TestDedupEmpresas(unittest.TestCase):
    """El alta desde leads-db no puede resucitar lo que la poda fusionó."""

    def test_names_similar_une_grafias_de_la_misma_empresa(self):
        import tracker
        self.assertTrue(tracker.names_similar("serasa", "serasaexperian"))
        self.assertTrue(tracker.names_similar("sumusica", "suamusica"))
        self.assertFalse(tracker.names_similar("", "acme"))

    def test_migracion_no_fusiona_marcas_de_otra_region(self):
        """'Patagonia' (US) y 'Patagonia IT' (LATAM) comparten prefijo, no empresa."""
        import json
        import tempfile

        reg = {"companies": {
            "patagonia": {"key": "patagonia", "name": "Patagonia",
                          "domain": "patagonia.com", "region": "us",
                          "status": "sin_tablero"},
        }}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "leads-db.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"2026-10-23": [{
                    "name": "Patagonia IT", "website": "https://patagonia-it.com",
                    "location": "Argentina"}]}, f)
            original, es.LEADS_DB = es.LEADS_DB, path
            try:
                added = es.migrate_leads_db({"companies": reg["companies"]})
            finally:
                es.LEADS_DB = original

        self.assertEqual(added, 1)
        self.assertIn("patagonia it", reg["companies"])

    def test_migracion_salta_duplicados_por_dominio_y_nombre(self):
        import json
        import tempfile
        import tracker

        reg = {"companies": {
            "serasa": {"key": "serasa", "name": "Serasa", "domain": "serasa.com.br",
                       "region": "latam", "status": "sin_vacante_flutter"},
        }}
        items = [{"last_updated": "2026-10-23", "companies": [
            # mismo dominio, otro nombre → duplicado
            {"name": "Serasa Experian", "website": "https://serasa.com.br"},
            # misma empresa con acento cambiado, otro dominio → duplicado
            {"name": "Sua Música", "website": "https://suamusica.com.br"},
            # empresa nueva de verdad → entra
            {"name": "Acme Mobile", "website": "https://acme.dev"},
        ]}]
        # "Su Musica" (sin acento) ya existe como clave canónica distinta.
        reg["companies"]["sumusica"] = {
            "key": "sumusica", "name": "Su Musica", "domain": "sumusica.app",
            "region": "latam", "status": "nuevo"}

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "leads-db.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"2026-10-23": items[0]["companies"]}, f)
            original, es.LEADS_DB = es.LEADS_DB, path
            try:
                added = es.migrate_leads_db({"companies": reg["companies"]})
            finally:
                es.LEADS_DB = original

        self.assertEqual(added, 1)
        self.assertIn("acme mobile", reg["companies"])
        self.assertNotIn("serasa experian", reg["companies"])
        self.assertEqual(tracker.canon_name("Sua Música"), "suamusica")


class TestPodarRegistro(unittest.TestCase):
    def setUp(self):
        import verificar_registro as vr
        self.vr = vr

    def test_marca_sin_dominio_y_fusiona_duplicados(self):
        reg = {"companies": {
            "seniorsistemas": {"key": "seniorsistemas", "name": "Senior Sistemas",
                               "domain": "senior.com.br", "region": "latam",
                               "status": "nuevo", "added": "2026-09-26"},
            "senior sistemas": {"key": "senior sistemas", "name": "Senior Sistemas",
                                "domain": "senior.com.br", "region": "latam",
                                "status": "con_vacante", "added": "2026-09-27",
                                "ats": "ashby", "slug": "senior", "open_roles": 2},
            "junk": {"key": "junk", "name": "Junk", "domain": "",
                     "region": "latam", "status": "nuevo", "added": "2026-09-26"},
        }}
        acciones = self.vr.podar_registro(reg)
        self.assertEqual(len(reg["companies"]), 2)
        self.assertEqual(reg["companies"]["junk"]["status"], "sin_dominio")
        vivo = reg["companies"]["senior sistemas"]
        self.assertEqual(vivo["ats"], "ashby")
        self.assertEqual(vivo["status"], "con_vacante")
        self.assertTrue(any("duplicado" in a for a in acciones))

    def test_poda_fusiona_variantes_de_acentuacion(self):
        reg = {"companies": {
            "sumusica": {"key": "sumusica", "name": "Su Musica",
                         "domain": "sumusica.app", "region": "latam",
                         "status": "sin_tablero", "added": "2026-09-26"},
            "sua música": {"key": "sua música", "name": "Sua Música",
                           "domain": "suamusica.com.br", "region": "latam",
                           "status": "sin_tablero", "added": "2026-10-23"},
        }}
        acciones = self.vr.podar_registro(reg)
        self.assertEqual(len(reg["companies"]), 1)
        self.assertTrue(any("duplicado" in a for a in acciones))

    def test_dry_run_no_modifica(self):
        reg = {"companies": {"junk": {"key": "junk", "name": "Junk", "domain": "",
                                      "status": "nuevo"}}}
        self.vr.podar_registro(reg, dry_run=True)
        self.assertEqual(reg["companies"]["junk"]["status"], "nuevo")

