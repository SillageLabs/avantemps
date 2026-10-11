import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from avantemps.ingest import fetch_roni, main
from test_storage import fixture


class MockResponse:
    def __init__(self, payload: bytes, url="https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"):
        self.payload = payload
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def geturl(self):
        return self.url

    def read(self, limit):
        return self.payload[:limit]


class IngestionTests(unittest.TestCase):
    def test_read_source_compatible_with_official_format(self):
        with patch("avantemps.ingest.urlopen", return_value=MockResponse(fixture().encode("ascii"))):
            self.assertEqual(fetch_roni().splitlines()[0], "SEAS YR ANOM")

    def test_external_redirect_refused(self):
        with patch("avantemps.ingest.urlopen",
                   return_value=MockResponse(b"bad", "https://example.com/RONI.ascii.txt")):
            with self.assertRaisesRegex(ValueError, "Redirection"):
                fetch_roni()

    def test_check_file_never_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            check = root / "test.txt"
            check.write_text(fixture(), encoding="ascii")
            with patch("sys.argv", ["ingest", "--check-file", str(check), "--data-dir", str(root / "data")]):
                with redirect_stdout(io.StringIO()) as log:
                    self.assertEqual(main(), 0)
                self.assertIn("sans import", log.getvalue())
            self.assertFalse((root / "data").exists())


if __name__ == "__main__":
    unittest.main()
