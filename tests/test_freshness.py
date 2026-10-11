"""Dates et instantanés synthétiques, sans valeur climatique mesurée."""
import unittest
from datetime import datetime, timedelta, timezone
from avantemps.freshness import assess_freshness


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 11, tzinfo=timezone.utc)
        self.snapshot = {"last_checked_at_utc": self.now.isoformat(),
                         "summary": {"latest": {"season": "JAS", "year": 2026}}}

    def test_two_independent_clocks_and_boundaries(self):
        report = assess_freshness(self.snapshot, self.now)
        self.assertEqual(report["status"], "within_internal_limits")
        self.assertEqual(report["observation_period_end"], "2026-09-30")
        self.snapshot["last_checked_at_utc"] = (self.now - timedelta(days=45)).isoformat()
        self.assertEqual(assess_freshness(self.snapshot, self.now)["reasons"], [])
        self.snapshot["last_checked_at_utc"] = (self.now - timedelta(days=45, seconds=1)).isoformat()
        self.assertEqual(assess_freshness(self.snapshot, self.now)["reasons"],
                         ["source_not_checked_recently"])
        self.snapshot["last_checked_at_utc"] = self.now.isoformat()
        self.snapshot["summary"]["latest"]["season"] = "MAM"
        self.assertEqual(assess_freshness(self.snapshot, self.now)["reasons"], ["observation_too_old"])
        self.snapshot["summary"]["latest"]["season"] = "JAS"
        for age, status in [(90, "within_internal_limits"), (91, "stale")]:
            now = datetime(2026, 9, 30, tzinfo=timezone.utc) + timedelta(days=age)
            self.snapshot["last_checked_at_utc"] = now.isoformat()
            self.assertEqual(assess_freshness(self.snapshot, now)["status"], status)

    def test_year_boundary_and_leap_month(self):
        for season, year, now, end in [
            ("NDJ", 2025, datetime(2026, 2, 1, tzinfo=timezone.utc), "2026-01-31"),
            ("DJF", 2024, datetime(2024, 3, 1, tzinfo=timezone.utc), "2024-02-29"),
        ]:
            self.snapshot["summary"]["latest"] = {"season": season, "year": year}
            self.snapshot["last_checked_at_utc"] = now.isoformat()
            self.assertEqual(assess_freshness(self.snapshot, now)["observation_period_end"], end)

    def test_unknown_dates_do_not_claim_freshness(self):
        for value in [None, "wrong", "2026-10-11T00:00:00", "2026-10-12T00:00:00+00:00"]:
            self.snapshot["last_checked_at_utc"] = value
            self.assertEqual(assess_freshness(self.snapshot, self.now)["status"], "unknown")
        del self.snapshot["last_checked_at_utc"]
        self.assertEqual(assess_freshness(self.snapshot, self.now)["status"], "unknown")
        self.snapshot["last_checked_at_utc"] = self.now.isoformat()
        self.snapshot["summary"]["latest"]["season"] = "NDJ"
        self.assertEqual(assess_freshness(self.snapshot, self.now)["status"], "unknown")
        with self.assertRaises(ValueError):
            assess_freshness(self.snapshot, datetime(2026, 10, 11))
