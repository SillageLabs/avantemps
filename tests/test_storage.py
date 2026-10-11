import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from avantemps.roni import SEASONS
from avantemps.storage import list_versions, load_latest, load_snapshot, store_snapshot


def fixture(change=0.0, extra=False):
    """Fausse série complète 1950→JAS 2026. Jamais des données NOAA réelles."""
    lines = ["SEAS YR ANOM"]
    for year in range(1950, 2027):
        seasons = SEASONS if year < 2026 else SEASONS[:(9 if extra else 8)]
        for season in seasons:
            value = (SEASONS.index(season) / 12) + (change if year == 2026 and season == "JAS" else 0)
            lines.append(f"{season} {year} {value:.2f}")
    return "\n".join(lines) + "\n"


class StoreTests(unittest.TestCase):
    def test_archive_immutable_and_last_checked_advances(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            t1 = datetime(2026, 10, 11, tzinfo=timezone.utc)
            t2 = datetime(2026, 10, 12, tzinfo=timezone.utc)
            first = store_snapshot(root, fixture(), t1)
            self.assertEqual(len(list_versions(root)), 1)
            self.assertTrue((root / "snapshots" / (first["id"] + ".txt")).exists())
            same = store_snapshot(root, fixture(), t2)
            self.assertEqual(same["retrieved_at_utc"], first["retrieved_at_utc"])
            self.assertEqual(load_latest(root)["last_checked_at_utc"], t2.isoformat())
            self.assertEqual(len(list_versions(root)), 1)
            second = store_snapshot(root, fixture(change=0.1), t2)
            self.assertNotEqual(first["id"], second["id"])
            self.assertEqual(load_latest(root)["id"], second["id"])
            self.assertEqual(len(list_versions(root)), 2)
            # Un fichier suspect ne doit jamais détruire le dernier état valide.
            with self.assertRaises(ValueError):
                store_snapshot(root, "SEAS YR ANOM\nDJF 2026 0.4\n", t2)
            self.assertEqual(load_latest(root)["id"], second["id"])

    def test_rejects_gaps_even_when_file_has_many_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lines = fixture().splitlines()
            lines.pop(250)
            with self.assertRaisesRegex(ValueError, "manquante"):
                store_snapshot(root, "\n".join(lines) + "\n")
            self.assertIsNone(load_latest(root))

    def test_integrity_detects_modified_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snap = store_snapshot(root, fixture())
            path = root / "snapshots" / (snap["id"] + ".txt")
            path.write_bytes(path.read_bytes() + b"extra")
            with self.assertRaisesRegex(ValueError, "altérée"):
                load_snapshot(root, snap["id"])

    def test_missing_archive_and_source_start(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(load_latest(root))
            self.assertEqual(list_versions(root), [])
            text = fixture()
            first_removed = "\n".join(text.splitlines()[2:]) + "\n"
            with self.assertRaises(ValueError):
                store_snapshot(root, "SEAS YR ANOM\n" + first_removed)


if __name__ == "__main__":
    unittest.main()
