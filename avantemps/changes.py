"""Comparer des versions de données : jamais confondre révisions et évolution du climat."""
from __future__ import annotations

from .roni import ORDER


def _records(snapshot: dict) -> dict[tuple[int, str], float]:
    return {(int(row["year"]), row["season"]): float(row["anomaly_c"])
            for row in snapshot["records"]}


def diff_snapshots(before: dict, after: dict) -> dict:
    """Differences entre deux publications du MÊME indice (pas deux saisons)."""
    old = _records(before)
    new = _records(after)
    changes = []
    for year, season in sorted(old.keys() | new.keys(), key=lambda key: (key[0], ORDER[key[1]])):
        key = year, season
        entry = {"year": year, "season": season}
        if key not in old:
            entry.update({"type": "added", "new_anomaly_c": new[key]})
        elif key not in new:
            entry.update({"type": "removed", "old_anomaly_c": old[key]})
        elif old[key] != new[key]:
            entry.update({
                "type": "revised",
                "old_anomaly_c": old[key],
                "new_anomaly_c": new[key],
                "delta_c": round(new[key] - old[key], 2),
            })
        else:
            continue
        changes.append(entry)
    return {
        "from": {"id": before["id"], "first_collected_at_utc": before["retrieved_at_utc"]},
        "to": {"id": after["id"], "first_collected_at_utc": after["retrieved_at_utc"]},
        "counts": {
            "added": sum(item["type"] == "added" for item in changes),
            "removed": sum(item["type"] == "removed" for item in changes),
            "revised": sum(item["type"] == "revised" for item in changes),
        },
        "changes": changes,
        "explanation": (
            "Différences entre deux archives NOAA, et NON variations entre "
            "saisons ni évolution d'un risque de catastrophe."
        ),
    }
