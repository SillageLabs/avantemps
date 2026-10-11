"""SYNTHETIC metadata only, not Copernicus observations or decoded GRIB."""
import copy
import unittest
from avantemps.cds_requests import plan
from avantemps.grib_coverage import forecast_coverage


def synthetic_messages(request):
    return [{'shortName': 'tp', 'centre': 'ecmf', 'system': int(request['system']),
             'dataDate': year * 10000 + request['init_month'] * 100 + 1,
             'dataTime': 0, 'number': member, 'forecastMonth': lead}
            for year in range(request['first_year'], request['last_year'] + 1)
            for member in range(1, 26)  # Do not assume numbering starts at zero.
            for lead in range(request['lead_month'], request['lead_month'] + 3)]


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.request = plan('ecmwf', '51', 1993, 2016, 11, 1)
        self.messages = synthetic_messages(self.request)

    def test_complete_headers_never_authorize_science_or_extraction(self):
        report = forecast_coverage(self.messages, self.request)
        self.assertEqual(report['status'], 'header_coverage_matches_plan')
        self.assertEqual(report['expected_messages_documented'], 1800)
        self.assertEqual(report['unique_valid_header_identities'], 1800)
        self.assertEqual(report['observed_member_ids'], list(range(1, 26)))
        self.assertFalse(report['scientific_validation_completed'])
        self.assertFalse(report['extraction_approved'])
        self.assertFalse(report['publication_authorized'])

    def test_missing_message_and_entire_member_are_distinguished(self):
        report = forecast_coverage(self.messages[:-1], self.request)
        self.assertEqual(report['missing_identity_count_for_observed_members'], 1)
        report = forecast_coverage([x for x in self.messages if x['number'] != 25], self.request)
        self.assertEqual(report['missing_identity_count_for_observed_members'], 0)
        self.assertEqual(len(report['observed_member_ids']), 24)
        self.assertEqual(report['status'], 'review_required')

    def test_duplicate_even_when_total_message_count_is_correct(self):
        messages = self.messages[:-1] + [self.messages[0]]
        report = forecast_coverage(messages, self.request)
        self.assertEqual(report['duplicate_identity_count'], 1)
        self.assertEqual(report['missing_identity_count_for_observed_members'], 1)
        self.assertEqual(report['status'], 'review_required')

    def test_version_lead_initialization_and_centre_must_match(self):
        for key, value in [('system', 5), ('forecastMonth', 6), ('dataDate', 19931102),
                           ('dataTime', 1200), ('centre', 'kwbc'), ('shortName', 't2m'),
                           ('number', None), ('forecastMonth', 1.0)]:
            with self.subTest(key=key, value=value):
                messages = copy.deepcopy(self.messages)
                messages[0][key] = value
                report = forecast_coverage(messages, self.request)
                self.assertEqual(report['invalid_message_count'], 1)
                self.assertEqual(report['status'], 'review_required')

    def test_lagged_nominal_dates_are_never_silently_mapped(self):
        self.messages[0]['indexingDate'] = 19931001
        report = forecast_coverage(self.messages, self.request)
        self.assertEqual(report['invalid_message_count'], 1)
        self.assertIn('nominale', report['invalid_examples'][0]['reason'])

    def test_member_numeric_alias_is_a_duplicate(self):
        alias = dict(self.messages[0], number='01')
        report = forecast_coverage(self.messages + [alias], self.request)
        self.assertEqual(report['duplicate_identity_count'], 1)

    def test_shifted_window_leads_are_explicit_not_inferred_from_validity_date(self):
        request = plan('ecmwf', '51', 1993, 2016, 12, 2)
        messages = synthetic_messages(request)
        self.assertEqual(forecast_coverage(messages, request)['status'], 'header_coverage_matches_plan')
        messages[0].pop('forecastMonth')
        messages[0]['validityDate'] = 19940101
        self.assertEqual(forecast_coverage(messages, request)['invalid_message_count'], 1)

    def test_empty_and_altered_plans_refused(self):
        with self.assertRaises(ValueError):
            forecast_coverage([], self.request)
        self.request['system'] = '5'
        with self.assertRaises(ValueError):
            forecast_coverage(self.messages, self.request)


if __name__ == '__main__':
    unittest.main()
