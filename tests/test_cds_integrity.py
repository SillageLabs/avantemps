"""Synthetic bytes are NOT Copernicus data or decodable scientific GRIB."""
import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch
from avantemps.cds_requests import plan, download, validate_plan
from avantemps.cds_integrity import verify_download, main


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        raw = b'GRIB' + b'SYNTHETIC_NOT_DATA' * 10 + b'7777'
        self.manifest = {
            'schema': 'avantemps.cds-download-manifest.v1',
            'publication_authorized': False,
            'downloaded_at_utc': '2026-10-11T18:00:00+00:00',
            'plan': plan('ecmwf', '5', 1993, 2016, 11, 1), 'artifacts': []}
        for role in ('forecast', 'observations'):
            filename = role + '.grib'
            (self.root / filename).write_bytes(raw)
            self.manifest['artifacts'].append({
                'role': role, 'filename': filename,
                'dataset': self.manifest['plan'][role]['dataset'],
                'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
        self.write_manifest()

    def write_manifest(self):
        (self.root / 'download-manifest.json').write_text(json.dumps(self.manifest))

    def test_match_never_means_scientific_approval_or_provider_authenticity(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = verify_download(self.root)
        self.assertEqual(result['status'], 'matches_local_manifest')
        for key in ('provider_authenticity_verified', 'scientific_validation_completed',
                    'extraction_approved', 'publication_authorized'):
            self.assertIs(result[key], False)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)

    def test_modified_content_same_length_and_truncation(self):
        path = self.root / 'forecast.grib'
        raw = path.read_bytes()
        path.write_bytes(raw[:20] + b'X' + raw[21:])
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            verify_download(self.root)
        path.write_bytes(raw[:-4])
        with self.assertRaisesRegex(ValueError, 'Taille'):
            verify_download(self.root)

    def test_wrong_roles_dataset_paths_hash_and_sizes(self):
        original = copy.deepcopy(self.manifest)
        mutations = [
            ('role', 'observations'), ('dataset', 'unknown'),
            ('filename', '../forecast.grib'), ('filename', '/etc/passwd'),
            ('sha256', 'not-a-hash'), ('bytes', True), ('bytes', 0)]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                self.manifest = copy.deepcopy(original)
                self.manifest['artifacts'][0][key] = value
                self.write_manifest()
                with self.assertRaises(ValueError):
                    verify_download(self.root)

    def test_missing_file_and_symlink(self):
        path = self.root / 'forecast.grib'
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'absent'):
            verify_download(self.root)
        path.symlink_to(self.root / 'observations.grib')
        with self.assertRaisesRegex(ValueError, 'symbolique'):
            verify_download(self.root)

    def test_invalid_manifest_and_timezone(self):
        original = copy.deepcopy(self.manifest)
        for key, value in [('publication_authorized', True), ('schema', 'other'),
                           ('downloaded_at_utc', '2026-10-11T18:00:00'),
                           ('downloaded_at_utc', '2026-10-11T18:00:00+02:00'),
                           ('artifacts', []), ('plan', None)]:
            with self.subTest(key=key, value=value):
                self.manifest = copy.deepcopy(original)
                self.manifest[key] = value
                self.write_manifest()
                with self.assertRaises(ValueError):
                    verify_download(self.root)

    def test_cli_invalid_manifest_fails_without_traceback(self):
        (self.root / 'download-manifest.json').write_text('[]')
        with patch('sys.argv', ['cds_integrity', str(self.root)]), redirect_stderr(io.StringIO()) as log:
            with self.assertRaises(SystemExit) as result:
                main()
        self.assertEqual(result.exception.code, 2)
        self.assertIn('Intégrité refusée', log.getvalue())

    def test_altered_plan_refused_before_client_or_directory_creation(self):
        request = copy.deepcopy(self.manifest['plan'])
        request['forecast']['request']['area'] = [90, -180, -90, 180]
        out = self.root / 'must-not-exist'
        with patch.dict('sys.modules', {'cdsapi': None}):
            with self.assertRaisesRegex(ValueError, 'modifié'):
                download(request, out)
        self.assertFalse(out.exists())
        request = copy.deepcopy(self.manifest['plan'])
        request['publication_authorized'] = 0
        with self.assertRaisesRegex(ValueError, 'modifié'):
            validate_plan(request)


if __name__ == '__main__':
    unittest.main()
