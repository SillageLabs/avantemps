"""All data in this file are SYNTHETIC, never scientific observations."""
import tempfile
import unittest
from pathlib import Path
from avantemps.grib_audit import audit_values, audit_grib


class ValueQualityTests(unittest.TestCase):
    def test_bitmap_not_sentinel_controls_missing(self):
        result = audit_values([9999, 9999, -1, float('nan'), float('inf'), 0], [0, 1, 1, 1, 1, 1])
        self.assertEqual(result['missing'], 1)
        self.assertEqual(result['nonfinite'], 2)
        self.assertEqual(result['negative'], 1)
        self.assertEqual(result['maximum_raw'], 9999)
        self.assertFalse(result['quality_flags_clear'])

    def test_empty_all_missing_and_clean(self):
        self.assertFalse(audit_values([])['quality_flags_clear'])
        self.assertIsNone(audit_values([9999], [0])['minimum_raw'])
        self.assertTrue(audit_values([0, .001])['quality_flags_clear'])

    def test_invalid_bitmap(self):
        for bitmap in ([], [2]):
            with self.assertRaises(ValueError):
                audit_values([1], bitmap)

    def test_encoded_synthetic_grib_roundtrip(self):
        try:
            import eccodes as ec
        except ImportError:
            self.skipTest('optional ecCodes absent')
        handle = ec.codes_grib_new_from_samples('regular_ll_sfc_grib2')
        try:
            ec.codes_set(handle, 'shortName', 'tp')
            count = ec.codes_get(handle, 'numberOfPoints')
            ec.codes_set(handle, 'bitmapPresent', 1)
            ec.codes_set(handle, 'missingValue', 9999)
            values = [0.001] * count
            values[0] = 9999
            ec.codes_set_values(handle, values)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'SYNTHETIC.grib'
                with path.open('wb') as output:
                    ec.codes_write(handle, output)
                before = path.read_bytes()
                metadata = audit_grib(path, 'observations')
                report = audit_grib(path, 'observations', inspect_values=True)
                self.assertFalse(metadata['values_inspected'])
                self.assertEqual(report['value_quality']['missing'], 1)
                self.assertEqual(report['value_quality']['valid'], count - 1)
                self.assertEqual(report['value_quality']['messages_with_flags'], 1)
                self.assertFalse(report['extraction_approved'])
                self.assertFalse(report['publication_authorized'])
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(report['sha256'], metadata['sha256'])
                # This encoded SYNTHETIC sample is not a seasonal CDS hindcast.
                from avantemps.cds_requests import plan
                coverage = audit_grib(path, 'forecast',
                                      request_plan=plan('ecmwf', '51', 1993, 2016, 11, 1))
                self.assertEqual(coverage['forecast_coverage']['status'], 'review_required')
                self.assertGreater(coverage['forecast_coverage']['invalid_message_count'], 0)
                self.assertFalse(coverage['extraction_approved'])
        finally:
            ec.codes_release(handle)
