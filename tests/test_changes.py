import unittest

from avantemps.changes import diff_snapshots


def snap(id, rows):
    return {"id": id, "retrieved_at_utc": "2026-10-11T00:00:00+00:00",
            "records": [{"year": year, "season": season, "anomaly_c": value}
                        for year, season, value in rows]}


class DiffTests(unittest.TestCase):
    def test_added_revised_removed_distinct_from_seasonal_change(self):
        before = snap("old", [(2026, "JJA", 0.5), (2026, "JAS", 1.2)])
        after = snap("new", [(2026, "JAS", 1.3), (2026, "ASO", 1.4)])
        result = diff_snapshots(before, after)
        self.assertEqual(result["counts"], {"added": 1, "removed": 1, "revised": 1})
        self.assertEqual([v["type"] for v in result["changes"]], ["removed", "revised", "added"])
        self.assertAlmostEqual(result["changes"][1]["delta_c"], 0.1)

    def test_change_of_whitespace_not_a_measurement_revision(self):
        records = [(2026, "JJA", 0.5)]
        result = diff_snapshots(snap("old", records), snap("new", records))
        self.assertEqual(result["changes"], [])
        self.assertEqual(result["counts"]["revised"], 0)


if __name__ == "__main__":
    unittest.main()
