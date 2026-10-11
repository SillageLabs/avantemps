"""Archivage de fichiers NOAA bruts immuables + état de dernière vérification."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .roni import EXPLANATION_URL, SOURCE_URL, latest_summary, parse_roni, validate_noaa_history

SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".avantemps-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _json_bytes(obj: dict) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _load_snapshot(root: Path, digest: str) -> dict:
    if not SHA_RE.fullmatch(digest):
        raise ValueError("Identifiant SHA-256 incorrect")
    directory = root / "snapshots"
    with (directory / f"{digest}.txt").open("rb") as stream:
        raw = stream.read()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Archive brute altérée (SHA-256)")
    with (directory / f"{digest}.json").open(encoding="utf-8") as stream:
        snapshot = json.load(stream)
    if snapshot["id"] != digest:
        raise ValueError("Archive JSON / source incohérentes")
    parsed = parse_roni(raw.decode("ascii"))
    if snapshot["records"] != [record.json() for record in parsed]:
        raise ValueError("Archive JSON / observations incohérentes")
    return snapshot


def store_snapshot(root: Path, text: str, retrieved_at: datetime | None = None) -> dict:
    """Valide totalement avant de toucher au pointeur courant.

    Le texte déjà archivé n'est jamais réécrit lors d'une collecte identique.
    """
    records = parse_roni(text)
    validate_noaa_history(records)
    now = retrieved_at if retrieved_at is not None else datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise ValueError("Date de collecte sans fuseau horaire")
    checked = now.astimezone(timezone.utc).isoformat()
    raw = text.encode("ascii")
    digest = hashlib.sha256(raw).hexdigest()
    directory = root / "snapshots"
    raw_path = directory / f"{digest}.txt"
    json_path = directory / f"{digest}.json"

    if json_path.exists():
        snapshot = _load_snapshot(root, digest)
    else:
        snapshot = {
            "id": digest,
            "source_url": SOURCE_URL,
            "explanation_url": EXPLANATION_URL,
            "index_name": "RONI",
            "unit": "degree_Celsius_anomaly",
            "retrieved_at_utc": checked,
            "note": "Date de première collecte, pas date de publication de la NOAA.",
            "summary": latest_summary(records),
            "records": [record.json() for record in records],
        }
        _atomic_bytes(raw_path, raw)
        _atomic_bytes(json_path, _json_bytes(snapshot))
    # last_checked décrit la dernière vérification RÉUSSIE, même sans changement de fichier.
    _atomic_bytes(root / "latest.json", _json_bytes({
        "snapshot_id": digest,
        "last_checked_at_utc": checked,
    }))
    return snapshot


def load_snapshot(root: Path, digest: str) -> dict:
    return _load_snapshot(root, digest)


def load_latest(root: Path) -> dict | None:
    pointer = root / "latest.json"
    if not pointer.is_file():
        return None
    with pointer.open(encoding="utf-8") as stream:
        state = json.load(stream)
    snapshot = _load_snapshot(root, state["snapshot_id"])
    snapshot["last_checked_at_utc"] = state.get("last_checked_at_utc", snapshot["retrieved_at_utc"])
    return snapshot


def list_versions(root: Path) -> list[dict]:
    directory = root / "snapshots"
    if not directory.exists():
        return []
    versions = []
    for path in directory.glob("*.json"):
        if not SHA_RE.fullmatch(path.stem):
            continue
        snapshot = _load_snapshot(root, path.stem)
        versions.append({
            "id": snapshot["id"],
            "retrieved_at_utc": snapshot["retrieved_at_utc"],
            "latest_observation": snapshot["summary"]["latest"],
        })
    return sorted(versions, key=lambda item: (item["retrieved_at_utc"], item["id"]), reverse=True)
