"""Inspection préalable NON destructive de GRIB C3S / ERA5 avec ecCodes.

Ne choisit pas de grille, ne rééchantillonne pas et n'autorise aucune publication.
Aucun accès réseau. Dépendance facultative : pip install eccodes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROLES = {"forecast", "observations"}
REQUIRED = ("shortName", "units", "dataDate", "dataTime", "gridType",
            "Ni", "Nj", "numberOfPoints", "latitudeOfFirstGridPointInDegrees",
            "longitudeOfFirstGridPointInDegrees", "latitudeOfLastGridPointInDegrees",
            "longitudeOfLastGridPointInDegrees")
OPTIONAL = ("number", "forecastMonth", "step", "stepType", "typeOfStatisticalProcessing",
            "generatingProcessIdentifier", "centre", "tablesVersion",
            "year", "month", "validityDate", "validityTime")


def audit_metadata(messages: list[dict], role: str) -> dict:
    """Validation des métadonnées, sans prétendre vérifier les valeurs physiques."""
    if role not in ROLES:
        raise ValueError("Rôle GRIB inconnu")
    if not messages:
        raise ValueError("Aucun message GRIB")
    units, grids, params, periods = set(), set(), set(), set()
    members, leads = set(), set()
    missing_keys = []
    for i, item in enumerate(messages):
        if not isinstance(item, dict):
            raise ValueError("Métadonnées de message GRIB malformées")
        absent = [key for key in REQUIRED if item.get(key) is None]
        if absent:
            missing_keys.append({"message": i+1, "keys": absent})
            continue
        if item["shortName"] != "tp":
            raise ValueError("Le fichier inclut un paramètre autre que total_precipitation (tp)")
        unit = str(item["units"])
        units.add(unit)
        params.add(str(item["shortName"]))
        grid = tuple(str(item[key]) for key in (
            "gridType", "Ni", "Nj", "numberOfPoints",
            "latitudeOfFirstGridPointInDegrees", "longitudeOfFirstGridPointInDegrees",
            "latitudeOfLastGridPointInDegrees", "longitudeOfLastGridPointInDegrees"
        ))
        grids.add(grid)
        periods.add(str(item["dataDate"]))
        if item.get("number") is not None:
            members.add(str(item["number"]))
        if item.get("forecastMonth") is not None:
            leads.add(str(item["forecastMonth"]))
    if missing_keys:
        raise ValueError(f"Clés GRIB absentes dans {len(missing_keys)} message(s) : {missing_keys[:3]}")
    expected_unit = "m s**-1" if role == "forecast" else "m day**-1"
    # Les représentations textuelles ecCodes peuvent différer : bloquer, inspecter.
    return {
        "schema": "avantemps.grib-audit.v1",
        "role": role,
        "messages": len(messages),
        "parameters": sorted(params),
        "units_detected": sorted(units),
        "expected_units_human": "m/s" if role == "forecast" else "m/day",
        "units_need_manual_confirmation": True,
        "grids_detected": len(grids),
        "grid_consistent": len(grids) == 1,
        "initialization_dates_count": len(periods),
        "member_ids_count": len(members),
        "forecast_months": sorted(leads),
        "publication_authorized": False,
        "extraction_approved": False,
        "issues": (
            ([] if len(grids) == 1 else ["Grilles multiples : extraction refusée"]) +
            ([] if len(units) == 1 else ["Unités multiples : extraction refusée"]) +
            ([] if role != "forecast" or members else ["Aucun identifiant de membre explicite"])
        ),
        "note": "Inventaire métadonnées uniquement, valeurs et géographie non vérifiées. "
                "Comparer aux plans CDS et inspecter les GRIB avant extraction.",
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_grib(path: Path, role: str) -> dict:
    """Lecture écCodes message par message ; les tableaux de points ne sont pas décodés."""
    if role not in ROLES:
        raise ValueError("Rôle GRIB incorrect")
    try:
        import eccodes
    except ImportError as exc:
        raise RuntimeError("ecCodes Python absent : installer eccodes localement") from exc
    if not path.is_file():
        raise ValueError("GRIB introuvable")
    if path.stat().st_size > 2_000_000_000:
        raise ValueError("GRIB > 2 Go : découper les fichiers avant audit")
    records = []
    with path.open("rb") as source:
        while True:
            handle = eccodes.codes_grib_new_from_file(source)
            if handle is None:
                break
            try:
                info = {}
                for key in REQUIRED + OPTIONAL:
                    try:
                        info[key] = eccodes.codes_get(handle, key)
                    except (eccodes.CodesInternalError, KeyError):
                        info[key] = None
                records.append(info)
                if len(records) > 100_000:
                    raise ValueError("Trop de messages GRIB pour le pré-audit")
            finally:
                eccodes.codes_release(handle)
    report = audit_metadata(records, role)
    report["file_size_bytes"] = path.stat().st_size
    report["sha256"] = _sha256(path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Pré-audit GRIB sans modification et sans publication")
    parser.add_argument("path", type=Path)
    parser.add_argument("--role", choices=sorted(ROLES), required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(audit_grib(args.path, args.role), ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"Audit refusé : {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
