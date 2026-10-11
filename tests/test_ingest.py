import io
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

from urllib.error import URLError
from avantemps.ingest import MAX_BYTES, fetch_roni, main
from avantemps.storage import store_snapshot
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

    def test_transport_timeout_and_size_limit(self):
        for error in (TimeoutError("synthetic timeout"), URLError("synthetic DNS error")):
            with self.subTest(error=type(error).__name__):
                with patch("avantemps.ingest.urlopen", side_effect=error):
                    with self.assertRaises(OSError):
                        fetch_roni()
        with patch("avantemps.ingest.urlopen", return_value=MockResponse(b"x" * (MAX_BYTES + 1))):
            with self.assertRaisesRegex(ValueError, "volumineux"):
                fetch_roni()

    def test_cli_failures_preserve_all_existing_archive_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store_snapshot(root, fixture())
            def contents():
                return {str(p.relative_to(root)): p.read_bytes()
                        for p in root.rglob('*') if p.is_file()}
            before = contents()
            failures = [TimeoutError("synthetic timeout"), URLError("synthetic DNS error"),
                        MockResponse(b"x" * (MAX_BYTES + 1)), MockResponse(b"\xff"),
                        MockResponse(b"truncated response")]
            for failure in failures:
                with self.subTest(failure=repr(failure)):
                    kwargs = ({"side_effect": failure} if isinstance(failure, Exception)
                              else {"return_value": failure})
                    with patch("avantemps.ingest.urlopen", **kwargs), \
                         patch("sys.argv", ["ingest", "--data-dir", str(root)]), \
                         redirect_stderr(io.StringIO()) as log:
                        self.assertEqual(main(), 1)
                        self.assertIn("archive inchangée", log.getvalue())
                    self.assertEqual(contents(), before)

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
