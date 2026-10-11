"""Données de tests purement synthétiques ; jamais des résultats NOAA/C3S."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from avantemps.verification import (
    evaluate, observed_categories, parse_pairs, quantile, rps, run,
    validate_manifest,
)


def meta():
    return {
        "schema": "avantemps.hindcast.v1",
        "dataset_kind": "retrospective_hindcast_pairs",
        "territory_id": "nouvelle-caledonie",
        "variable": "total_precipitation_mm",
        "forecast_system": "MODELE_SYNTHETIQUE_TEST",
        "system_version": "version-test",
        "spatial_method": "only synthetic values / no location",
        "forecast_tercile_method": "synthetic probabilities excluded from any publication",
        "observation_source_name": "synthetic unit test",
        "forecast_source_url": "https://example.org/synthetic-forecast",
        "observation_source_url": "https://example.org/synthetic-observation",
        "initialization_month": 1,
        "lead_month": 2,
        "target_window_months": 3,
        "start_year": 1993,
        "end_year": 2016,
        "cross_validation_declaration": "leave_one_year_out",
    }


def sample(n=24):
    return [{"year": 1993 + i, "p": (1/3, 1/3, 1/3), "observed_mm": 20.0 + 11 * i}
            for i in range(n)]


def csv_data(rows):
    lines = ["year,p_below,p_near,p_above,observed_mm"]
    for item in rows:
        p = item["p"]
        lines.append(f'{item["year"]},{p[0]},{p[1]},{p[2]},{item["observed_mm"]}')
    return "\n".join(lines) + "\n"


class VerificationTests(unittest.TestCase):
    def test_climatology_scores_zero_and_never_authorizes(self):
        rows = parse_pairs(csv_data(sample()), meta())
        report = evaluate(rows, meta())
        self.assertEqual(report["status"], "exploratory_only")
        self.assertAlmostEqual(report["skill"]["value"], 0, places=5)
        self.assertFalse(report["publication_authorized"])
        self.assertEqual(report["scientific_review"], "not_performed")
        self.assertEqual(report["n_distinct_years"], 24)

    def test_perfect_synthetic_oracle_scores_one_not_permission(self):
        rows = sample()
        categories = observed_categories(rows)
        for row, outcome in zip(rows, categories):
            row["p"] = tuple(float(i == outcome) for i in range(3))
        report = evaluate(rows, meta())
        self.assertEqual(report["skill"]["value"], 1)
        self.assertEqual(report["skill"]["bootstrap_percentile_95"], [1, 1])
        self.assertFalse(report["publication_authorized"])

    def test_wrong_forecast_is_negative(self):
        rows = sample()
        observed = observed_categories(rows)
        for row, category in zip(rows, observed):
            row["p"] = tuple(float(i == 2-category) for i in range(3))
        result = evaluate(rows, meta())
        self.assertLess(result["skill"]["value"], 0)

    def test_withhold_year_from_observation_quantiles(self):
        rows = sample()
        thresholds = [quantile([other["observed_mm"] for other in rows if other["year"] != row["year"]], 1/3)
                      for row in rows]
        self.assertGreater(thresholds[0], quantile([row["observed_mm"] for row in rows], 1/3))
        self.assertEqual(observed_categories(rows)[0], 0)
        self.assertEqual(observed_categories(rows)[-1], 2)

    def test_minimum_years_and_no_fake_skill(self):
        report = evaluate(sample(19), meta())
        self.assertEqual(report["status"], "insufficient_data")
        self.assertIsNone(report["skill"])
        self.assertFalse(report["publication_authorized"])

    def test_missing_year_prevents_score_even_above_minimum(self):
        for rows in (sample(20), sample()[:12] + sample()[13:]):
            with self.subTest(years=len(rows)):
                report = evaluate(rows, meta())
                self.assertEqual(report['status'], 'incomplete_period')
                self.assertIsNone(report['skill'])
                self.assertFalse(report['period_complete'])
                self.assertTrue(report['missing_years'])
                self.assertFalse(report['publication_authorized'])

    def test_direct_evaluation_cannot_bypass_input_validation(self):
        invalid = [('year', 1992), ('year', True), ('p', (0.2, 0.2, 0.2)),
                   ('p', (float('nan'), 0, 1)), ('p', (True, 0, 0)),
                   ('observed_mm', -1), ('observed_mm', float('inf'))]
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                rows = sample()
                rows[0][key] = value
                with self.assertRaises(ValueError):
                    evaluate(rows, meta())

    def test_complete_preregistered_shorter_period_remains_evaluable(self):
        manifest = meta()
        manifest['end_year'] = 2012
        report = evaluate(sample(20), manifest)
        self.assertEqual(report['status'], 'exploratory_only')
        self.assertTrue(report['period_complete'])
        self.assertEqual(report['expected_year_count'], 20)
        self.assertEqual(report['missing_years'], [])

    def test_rejects_invalid_probability_and_duplicate_year(self):
        rows = sample()
        text = csv_data(rows)
        with self.assertRaisesRegex(ValueError, "somme"):
            parse_pairs(text.replace("0.3333333333333333,0.3333333333333333,0.3333333333333333",
                                     "0.2,0.2,0.2", 1), meta())
        with self.assertRaises(ValueError):
            parse_pairs(text + text.splitlines()[1] + "\n", meta())
        with self.assertRaises(ValueError):
            parse_pairs(text.replace("0.3333333333333333", "nan", 1), meta())

    def test_invalid_manifest_and_unreviewed_claims(self):
        m = meta()
        m["forecast_source_url"] = "http://example.com/unsafe"
        with self.assertRaises(ValueError):
            validate_manifest(m)
        m = meta()
        m["cross_validation_declaration"] = "full_sample"
        with self.assertRaises(ValueError):
            validate_manifest(m)
        m = meta()
        m["variable"] = "local_disaster_prediction"
        with self.assertRaises(ValueError):
            validate_manifest(m)

    def test_tercile_ties_rejected(self):
        rows = sample()
        for row in rows:
            row["observed_mm"] = 100
        with self.assertRaisesRegex(ValueError, "Terciles"):
            evaluate(rows, meta())

    def test_cli_files_are_validated_without_export(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "meta.json").write_text(json.dumps(meta()), encoding="utf-8")
            (base / "pairs.csv").write_text(csv_data(sample()), encoding="utf-8")
            report = run(base / "meta.json", base / "pairs.csv")
            self.assertEqual(report["status"], "exploratory_only")
            self.assertEqual(len(report["input_sha256"]["manifest"]), 64)
            self.assertEqual(len(report["input_sha256"]["pairs"]), 64)
            self.assertFalse((base / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
