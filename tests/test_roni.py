import unittest

from avantemps.roni import parse_roni, latest_summary, signal


class ParseRoniTests(unittest.TestCase):
    def test_parser_and_observation_summary(self):
        rows = parse_roni("SEAS   YR  ANOM\nDJF 2025 -0.50\nJFM 2025 0.25\nFMA 2025 0.75\n")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1].season, "FMA")
        summary = latest_summary(rows)
        self.assertEqual(summary["signal"], "warm_index")
        self.assertEqual(summary["delta_from_previous_c"], 0.5)

    def test_boundaries_are_not_ensophase_claims(self):
        self.assertEqual(signal(0.50), "neutral_index")
        self.assertEqual(signal(-0.50), "neutral_index")
        self.assertEqual(signal(0.51), "warm_index")
        self.assertEqual(signal(-0.51), "cold_index")

    def test_invalid_header_and_empty(self):
        for bad in ("", "<html>Error</html>", "SEAS YR ANOM"):
            with self.subTest(input=bad):
                with self.assertRaises(ValueError):
                    parse_roni(bad)

    def test_refuses_duplicates_unsorted_bad_values(self):
        samples = (
            "SEAS YR ANOM\nDJF 2025 0.1\nDJF 2025 0.2\n",
            "SEAS YR ANOM\nJFM 2025 0.1\nDJF 2025 0.2\n",
            "SEAS YR ANOM\nDJF 2025 nan\n",
            "SEAS YR ANOM\nDJF 2025 inf\n",
            "SEAS YR ANOM\nDJF 2025 99\n",
            "SEAS YR ANOM\nXYZ 2025 1\n",
            "SEAS YR ANOM\nDJF 2025 nope\n",
        )
        for text in samples:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_roni(text)


if __name__ == "__main__":
    unittest.main()
