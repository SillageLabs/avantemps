import json
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from avantemps.server import Handler
from avantemps.storage import store_snapshot
from test_storage import fixture


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        directory = Path(self.tmp.name)
        self.handler = type("TestHandler", (Handler,), {"data_dir": directory})
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.data_dir = directory

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def read(self, path):
        with urlopen(self.base + path, timeout=5) as response:
            return response.status, json.load(response), response.headers

    def test_empty_and_invalid(self):
        status, data, _ = self.read("/api/health")
        self.assertEqual(status, 200)
        self.assertFalse(data["has_data"])
        with self.assertRaises(HTTPError) as err:
            urlopen(self.base + "/api/roni/latest", timeout=5)
        self.assertEqual(err.exception.code, 503)

    def test_comparison_and_provenance(self):
        t1 = datetime(2026, 10, 11, tzinfo=timezone.utc)
        old = store_snapshot(self.data_dir, fixture(), t1)
        _, empty, _ = self.read("/api/roni/changes")
        self.assertEqual(empty["status"], "insufficient_versions")
        store_snapshot(self.data_dir, fixture(change=0.1, extra=True), t1)
        _, latest, headers = self.read("/api/roni/latest")
        self.assertEqual(latest["index_name"], "RONI")
        self.assertIn("cpc.ncep.noaa.gov", latest["source_url"])
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertEqual(latest["last_checked_at_utc"], t1.isoformat())
        _, history, _ = self.read("/api/roni/history?limit=3")
        self.assertEqual(len(history["records"]), 3)
        _, versions, _ = self.read("/api/roni/versions")
        self.assertEqual(len(versions["versions"]), 2)
        _, revision, _ = self.read("/api/roni/changes")
        self.assertEqual(revision["status"], "ok")
        self.assertEqual(revision["comparison"]["counts"]["revised"], 1)
        self.assertEqual(revision["comparison"]["counts"]["added"], 1)
        self.assertEqual(revision["comparison"]["from"]["id"], old["id"])
        with self.assertRaises(HTTPError) as err:
            urlopen(self.base + "/api/roni/history?limit=999", timeout=5)
        self.assertEqual(err.exception.code, 400)
        with self.assertRaises(HTTPError) as err:
            urlopen(self.base + "/api/roni/changes?before=wrong&after=wrong", timeout=5)
        self.assertEqual(err.exception.code, 400)
        with self.assertRaises(HTTPError) as err:
            urlopen(self.base + "/api/roni/changes?before=" + old["id"], timeout=5)
        self.assertEqual(err.exception.code, 400)
        with self.assertRaises(HTTPError) as err:
            urlopen(self.base + "/api/unknown", timeout=5)
        self.assertEqual(err.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
