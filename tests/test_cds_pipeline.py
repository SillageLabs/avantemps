"""Fixtures 100 % SYNTHÉTIQUES : aucune performance climatique réelle."""
import csv
import io
import hashlib
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from avantemps.cds_requests import plan, months_for_window, shifted_month, download
from avantemps.pairing import (
    month_days, m_s_to_mm_month, m_day_to_mm_month, pair_from_monthlies,
)
from avantemps.verification import parse_pairs, evaluate


def fake_monthlies(request):
    """Deux CSV de grille fictive pour exercer le calcul et les changements d'année."""
    forecast = ["year,member,lead_month,tp_m_per_s"]
    observations = ["year,month,tp_m_per_day"]
    seen = set()
    for year in range(request["first_year"], request["last_year"] + 1):
        valid = months_for_window(year, request["init_month"], request["lead_month"])
        for offset, (actual_year, month) in enumerate(valid):
            if (actual_year, month) not in seen:
                seen.add((actual_year, month))
                observations.append(f"{actual_year},{month},{0.0007 + (year-1993)*0.00003 + offset*0.00001:.8f}")
            for member in range(4):
                rate = 0.0000004 * (1.0 + (year-1993)*0.09 + member*0.05 + offset*0.03)
                forecast.append(f"{year},{member},{request['lead_month']+offset},{rate:.12f}")
    return "\n".join(forecast) + "\n", "\n".join(observations) + "\n"


class CDSPlanTests(unittest.TestCase):
    def test_november_crosses_years_correctly(self):
        req = plan("ecmwf", "5", 1993, 2016, 11, 1)
        self.assertEqual(months_for_window(2016, 11, 1), [(2016, 11), (2016, 12), (2017, 1)])
        self.assertIn("2017", req["observations"]["request"]["year"])
        self.assertNotIn("2017", req["forecast"]["request"]["year"])
        self.assertEqual(req["forecast"]["request"]["leadtime_month"], ["1", "2", "3"])
        self.assertEqual(req["forecast"]["request"]["area"], [-19, 163, -23, 169])
        self.assertEqual(req["execution"], "not_performed")

    def test_start_lead_definition(self):
        self.assertEqual(months_for_window(1999, 12, 2), [(2000, 1), (2000, 2), (2000, 3)])
        self.assertEqual(shifted_month(2024, 12, 4), (2025, 4))

    def test_plan_rejects_unsupported_model_and_short_window(self):
        with self.assertRaisesRegex(ValueError, "modèle"):
            plan("unknown", "100", 1993, 2016, 11, 1)
        with self.assertRaisesRegex(ValueError, "20 années"):
            plan("ecmwf", "5", 2010, 2016, 11, 1)
        with self.assertRaises(ValueError):
            plan("ecmwf", "5", 1993, 2016, 11, 5)


class PairingTests(unittest.TestCase):
    def setUp(self):
        self.request = plan("ecmwf", "5", 1993, 2016, 11, 1)
        self.forecast, self.observation = fake_monthlies(self.request)

    def test_unit_conversion_and_leap_year(self):
        self.assertEqual(month_days(2000, 2), 29)
        self.assertEqual(month_days(2001, 2), 28)
        self.assertAlmostEqual(m_day_to_mm_month(0.001, 2000, 2), 29.0)
        self.assertAlmostEqual(m_s_to_mm_month(0.000001, 2000, 2), 2505.6)
        with self.assertRaises(ValueError):
            m_s_to_mm_month(-1, 2000, 2)

    def test_full_hindcast_pairing_and_exploratory_report(self):
        csv_text, prepared = pair_from_monthlies(self.request, self.forecast, self.observation)
        parsed = parse_pairs(csv_text, prepared["manifest"])
        self.assertEqual(len(parsed), 24)
        self.assertEqual(prepared["provenance"]["forecast_members"], 4)
        self.assertFalse(prepared["provenance"]["publication_authorized"])
        self.assertFalse(prepared["provenance"]["extraction_verified"])
        self.assertEqual(len(prepared["provenance"]["source_csv_sha256"]["forecast"]), 64)
        evaluated = evaluate(parsed, prepared["manifest"])
        self.assertEqual(evaluated["status"], "exploratory_only")
        self.assertFalse(evaluated["publication_authorized"])
        self.assertTrue(all(0 <= p <= 1 for row in parsed for p in row["p"]))

    def test_fails_for_missing_member_month(self):
        truncated = self.forecast.replace(self.forecast.splitlines()[-1] + "\n", "")
        with self.assertRaisesRegex(ValueError, "Prévision incomplète"):
            pair_from_monthlies(self.request, truncated, self.observation)

    def test_fails_for_missing_observation_month(self):
        truncated = self.observation.replace(self.observation.splitlines()[-1] + "\n", "")
        with self.assertRaisesRegex(ValueError, "Observation manquante"):
            pair_from_monthlies(self.request, self.forecast, truncated)

    def test_fails_if_negative_or_duplicate_values(self):
        with self.assertRaisesRegex(ValueError, "négative"):
            pair_from_monthlies(self.request, self.forecast.replace(",0.000000400000\n", ",-1.0\n", 1), self.observation)
        duplicate = self.forecast + self.forecast.splitlines()[1] + "\n"
        with self.assertRaisesRegex(ValueError, "dupliqué"):
            pair_from_monthlies(self.request, duplicate, self.observation)

    def test_modified_plan_is_rejected(self):
        altered = json.loads(json.dumps(self.request))
        altered["forecast"]["request"]["system"] = "999"
        with self.assertRaisesRegex(ValueError, "modifié"):
            pair_from_monthlies(altered, self.forecast, self.observation)

    def test_rejects_too_few_members(self):
        only_member_0 = "\n".join([self.forecast.splitlines()[0]] + [
            row for row in self.forecast.splitlines()[1:]
            if row.split(",")[1] == "0"]) + "\n"
        with self.assertRaisesRegex(ValueError, "membres"):
            pair_from_monthlies(self.request, only_member_0, self.observation)


class DownloadSafetyTests(unittest.TestCase):
    def test_opt_in_download_writes_sha256_manifest_without_loading_all_at_once(self):
        requested = []
        class FakeClient:
            def retrieve(self, dataset, args, target):
                requested.append(dataset)
                Path(target).write_bytes(b"GRIB" + b"synthetic-" * 15 + b"7777")

        module = types.SimpleNamespace(Client=lambda: FakeClient())
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "download"
            with patch.dict("sys.modules", {"cdsapi": module}):
                result = download(plan("ecmwf", "5", 1993, 2016, 11, 1), destination)
            self.assertEqual(requested, [
                "seasonal-monthly-single-levels",
                "reanalysis-era5-single-levels-monthly-means"
            ])
            self.assertFalse(result["publication_authorized"])
            for entry in result["artifacts"]:
                raw = (destination / entry["filename"]).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["sha256"])
                self.assertEqual(entry["bytes"], len(raw))
            with patch.dict("sys.modules", {"cdsapi": module}):
                with self.assertRaisesRegex(ValueError, "vide"):
                    download(plan("ecmwf", "5", 1993, 2016, 11, 1), destination)


if __name__ == "__main__":
    unittest.main()
