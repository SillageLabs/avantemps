"""Conserve chaque version NOAA, avec son texte brut, sans écraser l'historique."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .roni import EXPLANATION_URL, SOURCE_URL, latest_summary, parse_roni

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
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def store_snapshot(root: Path, text: str, retrieved_at: datetime | None = None) -> dict:
    # Toujours valider AVANT de toucher à l'état précédent.
    records = parse_roni(text)
    if len(records) < 100:
        raise ValueError("Source NOAA anormalement courte (< 100 saisons)")

    now = retrieved_at or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise ValueError("La date de collecte doit contenir un fuseau")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    directory = root / "snapshots"
    json_path = directory / f"{digest}.json"
    raw_path = directory / f"{digest}.txt"
    snapshot = {
        "id": digest,
        "source_url": SOURCE_URL,
        "explanation_url": EXPLANATION_URL,
        "index_name": "RONI",
        "unit": "degree_Celsius_anomaly",
        "retrieved_at_utc": now.astimezone(timezone.utc).isoformat(),
        "note": "Date de COLLECTE, pas date de publication NOAA.",
        "summary": latest_summary(records),
        "records": [record.json() for record in records],
    }
    if not json_path.exists():
        _atomic_bytes(raw_path, text.encode("utf-8"))
        _atomic_bytes(json_path, _json_bytes(snapshot))
    else:
        # Une version déjà archivée conserve la date de sa PREMIÈRE collecte.
        with json_path.open(encoding="utf-8") as stream:
            snapshot = json.load(stream)
    _atomic_bytes(root / "latest.json", _json_bytes({"snapshot_id": digest}))
    return snapshot


def load_latest(root: Path) -> dict | None:
    pointer = root / "latest.json"
    if not pointer.is_file():
        return None
    with pointer.open(encoding="utf-8") as stream:
        digest = json.load(stream)["snapshot_id"]
    if not isinstance(digest, str) or not SHA_RE.fullmatch(digest):
        raise ValueError("Index d'archive invalide")
    with (root / "snapshots" / f"{digest}.json").open(encoding="utf-8") as stream:
        return json.load(stream)


def list_versions(root: Path) -> list[dict]:
    directory = root / "snapshots"
    if not directory.exists():
        return []
    versions = []
    for path in directory.glob("*.json"):
        if not SHA_RE.fullmatch(path.stem):
            continue
        with path.open(encoding="utf-8") as stream:
            snapshot = json.load(stream)
        versions.append({
            "id": snapshot["id"],
            "retrieved_at_utc": snapshot["retrieved_at_utc"],
            "latest_observation": snapshot["summary"]["latest"],
        })
    return sorted(versions, key=lambda item: (item["retrieved_at_utc"], item["id"]), reverse=True)
