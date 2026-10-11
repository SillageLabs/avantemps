"""Tests de sûreté du catalogue : aucune conclusion sans source et sans statut."""
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

from avantemps import territories
from avantemps.server import Handler


class TerritoryRegistryTests(unittest.TestCase):
    def test_registry_is_valid_and_claims_have_primary_sources(self):
        territories.validate_registry()
        nc = territories.get_territory("nouvelle-caledonie")
        self.assertEqual(nc["status"], "documented_climatology")
        self.assertTrue(nc["climatology"])
        self.assertTrue(nc["dated_publications"])
        for claim in nc["climatology"] + nc["dated_publications"]:
            self.assertTrue(claim["source_ids"])
            self.assertNotIn("risk_score", claim)
            self.assertNotIn("alert_level", claim)
            for key in claim["source_ids"]:
                self.assertIn(key, nc["sources"])
                self.assertIn("https://meteo.nc/", nc["sources"][key]["url"])

    def test_abstention_is_explicit_for_unstudied_territories(self):
        for region in ("nantes", "guyane"):
            profile = territories.get_territory(region)
            self.assertEqual(profile["status"], "not_assessed")
            self.assertEqual(profile["climatology"], [])
            self.assertEqual(profile["dated_publications"], [])
            self.assertIn("abstient", profile["conclusion"])
        self.assertIsNone(territories.get_territory("inconnue"))

    def test_profile_is_immutable_from_callers(self):
        nc = territories.get_territory("nouvelle-caledonie")
        nc["climatology"][0]["detail"] = "Donnée inventée"
        self.assertNotEqual(nc["climatology"][0]["detail"],
                            territories.get_territory("nouvelle-caledonie")["climatology"][0]["detail"])

    def test_registry_rejects_unsourced_or_risk_score(self):
        with patch.dict(territories.PROFILES, {}, clear=False):
            nc = territories.PROFILES["nouvelle-caledonie"]
            with patch.dict(nc["climatology"][0], {"source_ids": []}):
                with self.assertRaises(ValueError):
                    territories.validate_registry()
            with patch.dict(nc["climatology"][0], {"risk_score": 85}):
                with self.assertRaises(ValueError):
                    territories.validate_registry()


class TerritoryApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        handler = type("TestTerritories", (Handler,),
                       {"data_dir": Path(self.tmp.name)})
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def get(self, suffix):
        with urlopen(self.base + suffix, timeout=5) as response:
            return response.status, json.load(response)

    def test_profiles_work_without_noaa_archive(self):
        code, health = self.get("/api/health")
        self.assertEqual(code, 200)
        self.assertFalse(health["has_data"])
        code, listing = self.get("/api/territories")
        self.assertEqual(code, 200)
        self.assertIn("nouvelle-caledonie", [x["id"] for x in listing["territories"]])
        code, profile = self.get("/api/territories/nouvelle-caledonie")
        self.assertEqual(code, 200)
        self.assertEqual(profile["status"], "documented_climatology")
        self.assertTrue(profile["sources"])
        self.assertTrue(profile["climatology"])
        self.assertNotIn("local_forecast", profile)
        _, nantes = self.get("/api/territories/nantes")
        self.assertEqual(nantes["status"], "not_assessed")

    def test_unknown_territory_returns_404(self):
        for suffix in ("/api/territories/unknown", "/api/territories/nantes/extra"):
            with self.assertRaises(HTTPError) as error:
                urlopen(self.base + suffix, timeout=5)
            self.assertEqual(error.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
