"""Declared forecast coverage check, limited to ECMWF burst hindcasts.

This checks header identities, not physical values, spatial representativeness
or licence/provider authenticity. No inferred leads or silent date conversion.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from .cds_requests import validate_plan

DOC = 'https://confluence.ecmwf.int/spaces/CKB/pages/77213502/Description+of+the+C3S+seasonal+multi-system'
EXPECTED_MEMBERS = 25


def _integer(value, key: str) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return int(value)
    raise ValueError('Clé GRIB entière explicite requise : ' + key)


def forecast_coverage(messages: list[dict], request_plan: dict) -> dict:
    validate_plan(request_plan)
    if not messages:
        raise ValueError('Aucun message pour le contrôle de couverture')
    identities = Counter()
    members = set()
    expected_dates = {y * 10000 + request_plan['init_month'] * 100 + 1
                      for y in range(request_plan['first_year'], request_plan['last_year'] + 1)}
    expected_leads = set(range(request_plan['lead_month'], request_plan['lead_month'] + 3))
    invalid = []
    for index, item in enumerate(messages, 1):
        if not isinstance(item, dict):
            raise ValueError('Métadonnées GRIB malformées')
        try:
            date = _integer(item.get('dataDate'), 'dataDate')
            datetime.strptime(str(date), '%Y%m%d')
            time = _integer(item.get('dataTime'), 'dataTime')
            member = _integer(item.get('number'), 'number')
            lead = _integer(item.get('forecastMonth'), 'forecastMonth')
            system = _integer(item.get('system'), 'system')
            if system != int(request_plan['system']):
                raise ValueError('Version du système différente du plan')
            if item.get('shortName') != 'tp':
                raise ValueError('Paramètre autre que tp')
            if str(item.get('centre')) not in ('ecmf', '98'):
                raise ValueError('Centre ECMWF explicite requis')
            if date not in expected_dates or time != 0:
                raise ValueError('Initialisation hors plan ECMWF burst')
            if lead not in expected_leads or not 0 <= member < 200:
                raise ValueError('Membre ou forecastMonth hors bornes')
            # Selected ECMWF systems are burst; never silently map lagged starts.
            if item.get('indexingDate') is not None and _integer(item['indexingDate'], 'indexingDate') != date:
                raise ValueError('Dates réelle et nominale différentes : inspection requise')
            if item.get('indexingTime') is not None and _integer(item['indexingTime'], 'indexingTime') != time:
                raise ValueError('Heures réelle et nominale différentes : inspection requise')
        except ValueError as exc:
            invalid.append({'message': index, 'reason': str(exc)})
            continue
        members.add(member)
        identities[(date, member, lead)] += 1
    expected = {(date, member, lead) for date in expected_dates
                for member in members for lead in expected_leads}
    missing = sorted(expected - identities.keys())
    duplicates = sorted(key for key, count in identities.items() if count > 1)
    issues = []
    if invalid:
        issues.append('Métadonnées absentes ou hors plan')
    if len(members) != EXPECTED_MEMBERS:
        issues.append('Nombre de membres différent des 25 hindcasts ECMWF documentés')
    if missing:
        issues.append('Combinaisons initialisation/membre/échéance manquantes')
    if duplicates:
        issues.append('Messages dupliqués pour une même identité')
    return {
        'schema': 'avantemps.grib-forecast-coverage.v1',
        'status': 'header_coverage_matches_plan' if not issues else 'review_required',
        'expected_member_count': EXPECTED_MEMBERS,
        'observed_member_ids': sorted(members),
        'expected_initializations': len(expected_dates),
        'expected_leads': sorted(expected_leads),
        'expected_messages_documented': len(expected_dates) * EXPECTED_MEMBERS * len(expected_leads),
        'unique_valid_header_identities': len(identities),
        'invalid_message_count': len(invalid), 'invalid_examples': invalid[:10],
        'missing_identity_count_for_observed_members': len(missing),
        'missing_examples': [list(key) for key in missing[:10]],
        'duplicate_identity_count': len(duplicates),
        'duplicate_examples': [list(key) for key in duplicates[:10]],
        'issues': issues, 'reference': DOC,
        'scientific_validation_completed': False,
        'extraction_approved': False, 'publication_authorized': False,
        'note': 'Identifiants membres observés, non supposés 0-24. Vérifier aussi unités, périodes de moyenne, coordonnées et valeurs réelles. ERA5 non couvert par ce contrôle.',
    }
