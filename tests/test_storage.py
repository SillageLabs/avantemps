import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from avantemps.roni import SEASONS
from avantemps.storage import list_versions, load_latest, store_snapshot


def fixture(change=0.0):
    lines = ["SEAS YR ANOM"]
    for year in range(2018, 2027):
        for i, season in enumerate(SEASONS):
            value = (i / 12) + (change if (year, i) == (2026, 11) else 0)
            lines.append(f"{season} {year} {value:.2f}")
    return "\n".join(lines) + "\n"


class StoreTests(unittest.TestCase):
    def test_immutable_snapshots_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            now = datetime(2026, 10, 11, tzinfo=timezone.utc)
            first = store_snapshot(root, fixture(), now)
            self.assertEqual(len(list_versions(root)), 1)
            self.assertTrue((root / "snapshots" / (first["id"] + ".txt")).exists())
            again = store_snapshot(root, fixture(), datetime(2026, 10, 12, tzinfo=timezone.utc))
            self.assertEqual(again["retrieved_at_utc"], first["retrieved_at_utc"])
            self.assertEqual(len(list_versions(root)), 1)
            second = store_snapshot(root, fixture(change=0.1), now)
            self.assertNotEqual(first["id"], second["id"])
            self.assertEqual(load_latest(root)["id"], second["id"])
            self.assertEqual(len(list_versions(root)), 2)
            with self.assertRaises(ValueError):
                store_snapshot(root, "SEAS YR ANOM\nDJF 2026 0.4\n", now)
            self.assertEqual(load_latest(root)["id"], second["id"])

    def test_missing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(load_latest(root))
            self.assertEqual(list_versions(root), [])


if __name__ == "__main__":
    unittest.main()
