"""Inspection préalable NON destructive de GRIB C3S / ERA5 avec ecCodes.

Ne choisit pas de grille, ne rééchantillonne pas et n'autorise aucune publication.
Aucun accès réseau. Dépendance facultative : pip install eccodes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROLES = {"forecast", "observations"}
REQUIRED = ("shortName", "units", "dataDate", "dataTime", "gridType",
            "Ni", "Nj", "numberOfPoints", "latitudeOfFirstGridPointInDegrees",
            "longitudeOfFirstGridPointInDegrees", "latitudeOfLastGridPointInDegrees",
            "longitudeOfLastGridPointInDegrees")
OPTIONAL = ("number", "forecastMonth", "step", "stepType", "typeOfStatisticalProcessing",
            "generatingProcessIdentifier", "centre", "tablesVersion",
            "year", "month", "validityDate", "validityTime",
            "indexingDate", "indexingTime", "localDefinitionNumber",
            "iDirectionIncrementInDegrees", "jDirectionIncrementInDegrees",
            "iScansNegatively", "jScansPositively", "jPointsAreConsecutive",
            "alternativeRowScanning", "md5GridSection")


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
        # Include scanning order and resolution: endpoints alone are insufficient.
        grid += tuple(str(item.get(key)) for key in OPTIONAL[-7:])
        grids.add(grid)
        periods.add(str(item["dataDate"]))
        if item.get("number") is not None:
            members.add(str(item["number"]))
        if item.get("forecastMonth") is not None:
            leads.add(str(item["forecastMonth"]))
    if missing_keys:
        raise ValueError(f"Clés GRIB absentes dans {len(missing_keys)} message(s) : {missing_keys[:3]}")
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


def audit_values(values, bitmap=None) -> dict:
    """Raw values only; bitmap, never sentinel equality, identifies missing points.

    No clipping, unit conversion, spatial aggregation or skill calculation.
    """
    if bitmap is not None and len(bitmap) != len(values):
        raise ValueError("Bitmap et valeurs de tailles différentes")
    missing = nonfinite = negative = valid = 0
    minimum = maximum = None
    for index, raw in enumerate(values):
        if bitmap is not None:
            if bitmap[index] not in (0, 1):
                raise ValueError("Bitmap GRIB invalide")
            if bitmap[index] == 0:
                missing += 1
                continue
        value = float(raw)
        if not math.isfinite(value):
            nonfinite += 1
            continue
        valid += 1
        negative += value < 0
        minimum = value if minimum is None else min(minimum, value)
        maximum = value if maximum is None else max(maximum, value)
    return {"points": len(values), "missing": missing, "nonfinite": nonfinite,
            "negative": negative, "valid": valid, "minimum_raw": minimum,
            "maximum_raw": maximum,
            "quality_flags_clear": bool(valid) and not (missing or nonfinite or negative)}


def audit_grib(path: Path, role: str, *, inspect_values: bool = False) -> dict:
    """Lecture ecCodes ; décodage des valeurs uniquement sur demande explicite."""
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
    value_reports = []
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
                if inspect_values:
                    if info.get("numberOfPoints") is None or not 0 < info["numberOfPoints"] <= 1_000_000:
                        raise ValueError("Nombre de points hors limite du contrôle local")
                    values = eccodes.codes_get_values(handle)
                    if len(values) != info["numberOfPoints"]:
                        raise ValueError("Nombre de valeurs incohérent")
                    bitmap = (eccodes.codes_get_array(handle, "bitmap")
                              if eccodes.codes_get(handle, "bitmapPresent") else None)
                    value_reports.append(audit_values(values, bitmap))
                if len(records) > 100_000:
                    raise ValueError("Trop de messages GRIB pour le pré-audit")
            finally:
                eccodes.codes_release(handle)
    report = audit_metadata(records, role)
    report["values_inspected"] = inspect_values
    if inspect_values:
        report["value_quality"] = {
            "messages_with_flags": sum(not r["quality_flags_clear"] for r in value_reports),
            **{key: sum(r[key] for r in value_reports)
               for key in ("points", "missing", "nonfinite", "negative", "valid")},
            "per_message": value_reports,
        }
        if report["value_quality"]["messages_with_flags"]:
            report["issues"].append("Valeurs manquantes/non finies/négatives : revue requise")
    report["file_size_bytes"] = path.stat().st_size
    report["sha256"] = _sha256(path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Pré-audit GRIB sans modification et sans publication")
    parser.add_argument("path", type=Path)
    parser.add_argument("--role", choices=sorted(ROLES), required=True)
    parser.add_argument("--inspect-values", action="store_true",
                        help="Décode les valeurs brutes et le bitmap, sans extraction")
    args = parser.parse_args()
    try:
        print(json.dumps(audit_grib(args.path, args.role, inspect_values=args.inspect_values), ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"Audit refusé : {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
