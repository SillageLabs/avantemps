"""Offline identity check of the two downloaded artifacts; no scientific approval.

A manifest is a local declaration, not a provider signature or licence proof.
No network, extraction, service, or write operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from .cds_requests import validate_plan

MAX_MANIFEST_BYTES = 100_000
MAX_GRIB_BYTES = 2_000_000_000


def verify_download(directory: Path) -> dict:
    manifest_path = directory / "download-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("Manifeste absent ou lien symbolique")
    if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Manifeste trop volumineux")
    with manifest_path.open('rb') as source:
        raw = source.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Manifeste trop volumineux")
    manifest = json.loads(raw)
    if not isinstance(manifest, dict) or manifest.get('schema') != 'avantemps.cds-download-manifest.v1':
        raise ValueError("Schéma du manifeste invalide")
    if manifest.get('publication_authorized') is not False:
        raise ValueError("Publication doit rester interdite")
    validate_plan(manifest.get('plan'))
    try:
        timestamp = datetime.fromisoformat(manifest['downloaded_at_utc'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Date de collecte invalide") from exc
    if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
        raise ValueError("Date de collecte UTC explicite requise")
    artifacts = manifest.get('artifacts')
    if not isinstance(artifacts, list) or len(artifacts) != 2:
        raise ValueError("Deux artefacts attendus")
    seen = set()
    verified = []
    for item in artifacts:
        if not isinstance(item, dict):
            raise ValueError("Artefact malformé")
        role = item.get('role')
        if role not in ('forecast', 'observations') or role in seen:
            raise ValueError("Rôles invalides ou dupliqués")
        seen.add(role)
        if item.get('dataset') != manifest['plan'][role]['dataset']:
            raise ValueError("Jeu de données incohérent avec le plan")
        # Only fixed basenames; never open an arbitrary path from the manifest.
        filename = role + '.grib'
        if item.get('filename') != filename:
            raise ValueError("Nom de fichier non autorisé")
        expected_bytes = item.get('bytes')
        if type(expected_bytes) is not int or not 100 <= expected_bytes <= MAX_GRIB_BYTES:
            raise ValueError("Taille déclarée invalide")
        expected_hash = item.get('sha256')
        if not isinstance(expected_hash, str) or not re.fullmatch('[0-9a-f]{64}', expected_hash):
            raise ValueError("SHA-256 déclaré invalide")
        path = directory / filename
        if path.is_symlink() or not path.is_file():
            raise ValueError("GRIB absent ou lien symbolique")
        digest = hashlib.sha256()
        actual_bytes = 0
        with path.open('rb') as source:
            if source.read(4) != b'GRIB':
                raise ValueError("Réponse non GRIB")
            source.seek(0)
            while chunk := source.read(1024 * 1024):
                actual_bytes += len(chunk)
                if actual_bytes > expected_bytes:
                    raise ValueError("Taille du GRIB différente du manifeste")
                digest.update(chunk)
            if actual_bytes != expected_bytes:
                raise ValueError("Taille du GRIB différente du manifeste")
            source.seek(-4, 2)
            if source.read(4) != b'7777':
                raise ValueError("Fin GRIB absente")
        if digest.hexdigest() != expected_hash:
            raise ValueError("SHA-256 du GRIB différent du manifeste")
        verified.append({'role': role, 'filename': filename, 'bytes': actual_bytes,
                         'sha256': digest.hexdigest()})
    return {'schema': 'avantemps.cds-integrity.v1',
            'status': 'matches_local_manifest',
            'manifest_sha256': hashlib.sha256(raw).hexdigest(),
            'artifacts': verified,
            'provider_authenticity_verified': False,
            'scientific_validation_completed': False,
            'extraction_approved': False, 'publication_authorized': False,
            'note': 'Identité locale uniquement ; ni décodage GRIB ni preuve de provenance CDS.'}


def main() -> int:
    parser = argparse.ArgumentParser(description='Contrôle local des empreintes CDS, sans réseau ni écriture')
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify_download(args.directory), ensure_ascii=False, indent=2))
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(2, f'Intégrité refusée : {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
