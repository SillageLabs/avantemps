import unittest
from avantemps.grib_audit import audit_metadata


def sample(**kwargs):
    record = {
        "shortName": "tp", "units": "m s**-1", "dataDate": 19931101,
        "dataTime": 0, "gridType": "regular_ll", "Ni": 6, "Nj": 6,
        "numberOfPoints": 36,
        "latitudeOfFirstGridPointInDegrees": -19,
        "longitudeOfFirstGridPointInDegrees": 163,
        "latitudeOfLastGridPointInDegrees": -23,
        "longitudeOfLastGridPointInDegrees": 169,
        "number": 0, "forecastMonth": 1
    }
    record.update(kwargs)
    return record


class GribAuditTests(unittest.TestCase):
    def test_summary_is_non_publishing(self):
        result = audit_metadata([sample(), sample(number=1, forecastMonth=2)], "forecast")
        self.assertEqual(result["messages"], 2)
        self.assertTrue(result["grid_consistent"])
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["extraction_approved"])
        self.assertEqual(result["member_ids_count"], 2)
        self.assertTrue(result["units_need_manual_confirmation"])

    def test_rejects_wrong_variable(self):
        with self.assertRaisesRegex(ValueError, "total_precipitation"):
            audit_metadata([sample(shortName="t2m")], "observations")

    def test_rejects_missing_required_geometry(self):
        with self.assertRaisesRegex(ValueError, "Clés GRIB absentes"):
            audit_metadata([sample(Ni=None)], "forecast")

    def test_warns_on_inconsistent_grid_and_units(self):
        result = audit_metadata([sample(), sample(Ni=7, units="unknown")], "forecast")
        self.assertFalse(result["grid_consistent"])
        self.assertEqual(len(result["issues"]), 2)

    def test_empty_or_bad_role(self):
        with self.assertRaises(ValueError):
            audit_metadata([], "forecast")
        with self.assertRaises(ValueError):
            audit_metadata([sample()], "unknown")


if __name__ == "__main__":
    unittest.main()
