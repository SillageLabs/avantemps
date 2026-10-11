"""Évaluateur exploratoire de prévisions saisonnières rétrospectives.

Ne publie aucun résultat et ne calcule aucun risque de catastrophe.
"""
from __future__ import annotations

import argparse
import csv
import io
import hashlib
import json
import math
import random
import statistics
from pathlib import Path
from urllib.parse import urlparse

SCHEMA = "avantemps.hindcast.v1"
COLS = ("year", "p_below", "p_near", "p_above", "observed_mm")
MIN_YEARS = 20
MAX_CSV_BYTES = 1_000_000
N_BOOTSTRAPS = 1000
SEED = 20261011


def validate_manifest(meta: dict) -> dict:
    """Ces renseignements sont déclaratifs et devront être audités."""
    if not isinstance(meta, dict) or meta.get("schema") != SCHEMA:
        raise ValueError("Schéma de manifeste invalide")
    required = ("territory_id", "forecast_system", "system_version", "spatial_method",
                "forecast_tercile_method", "observation_source_name")
    for key in required:
        value = meta.get(key)
        if not isinstance(value, str) or not (3 <= len(value.strip()) <= 300):
            raise ValueError("Métadonnée obligatoire absente : " + key)
    if meta.get("variable") != "total_precipitation_mm":
        raise ValueError("Seules les précipitations en mm sont supportées en v0.1")
    if meta.get("dataset_kind") != "retrospective_hindcast_pairs":
        raise ValueError("Type de données inadéquat")
    for key in ("forecast_source_url", "observation_source_url"):
        url = meta.get(key)
        if not isinstance(url, str):
            raise ValueError("URL de provenance requise : " + key)
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("URL HTTPS de provenance requise : " + key)
    for key, lower, upper in (("initialization_month", 1, 12), ("lead_month", 1, 6),
                              ("start_year", 1900, 2100), ("end_year", 1900, 2100)):
        if type(meta.get(key)) is not int or not (lower <= meta[key] <= upper):
            raise ValueError("Métadonnée numérique invalide : " + key)
    if meta["start_year"] > meta["end_year"]:
        raise ValueError("Période inversée")
    if meta.get("target_window_months") != 3:
        raise ValueError("Uniquement les cumuls de 3 mois sont évalués")
    if meta.get("cross_validation_declaration") != "leave_one_year_out":
        raise ValueError("Validation hors année cible non déclarée")
    return meta


def parse_pairs(text: str, meta: dict) -> list[dict]:
    validate_manifest(meta)
    if len(text.encode("utf-8")) > MAX_CSV_BYTES:
        raise ValueError("CSV trop volumineux")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != list(COLS):
        raise ValueError("Colonnes attendues : " + ",".join(COLS))
    result, years = [], set()
    for row_no, record in enumerate(reader, 2):
        if None in record or any(v is None for v in record.values()):
            raise ValueError(f"CSV malformé ligne {row_no}")
        try:
            year = int(record["year"])
            probs = (float(record["p_below"]), float(record["p_near"]), float(record["p_above"]))
            observed = float(record["observed_mm"])
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Nombre incorrect ligne {row_no}") from exc
        if year in years or not (meta["start_year"] <= year <= meta["end_year"]):
            raise ValueError("Année dupliquée ou hors période")
        years.add(year)
        if not all(math.isfinite(p) and 0 <= p <= 1 for p in probs):
            raise ValueError("Probabilités invalides")
        if abs(sum(probs) - 1) > 1e-6:
            raise ValueError("Les probabilités doivent sommer à 1")
        if not math.isfinite(observed) or observed < 0:
            raise ValueError("Observation en mm non valide")
        result.append({"year": year, "p": probs, "observed_mm": observed})
    if not result:
        raise ValueError("Aucune paire hindcast/observation")
    return sorted(result, key=lambda item: item["year"])


def quantile(values: list[float], q: float) -> float:
    sorted_vals = sorted(values)
    pos = (len(sorted_vals) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return sorted_vals[lo] + (pos - lo) * (sorted_vals[hi] - sorted_vals[lo])


def observed_categories(rows: list[dict]) -> list[int]:
    """Exclut l'année cible de tous les seuils observationnels."""
    result = []
    for row in rows:
        train = [other["observed_mm"] for other in rows if other["year"] != row["year"]]
        if len(train) < 2:
            raise ValueError("Trop peu d'années pour des terciles hors échantillon")
        low, high = quantile(train, 1 / 3), quantile(train, 2 / 3)
        if low >= high:
            raise ValueError("Terciles impossibles : climatologie non discriminante")
        value = row["observed_mm"]
        result.append(0 if value < low else 2 if value > high else 1)
    return result


def rps(p: tuple[float, float, float], category: int) -> float:
    if category not in (0, 1, 2):
        raise ValueError("Catégorie observée invalide")
    return ((p[0] - (1 if category == 0 else 0)) ** 2
            + (p[0] + p[1] - (1 if category <= 1 else 0)) ** 2)


def skill(pairs: list[tuple[float, float]]) -> float:
    model = statistics.fmean(pair[0] for pair in pairs)
    baseline = statistics.fmean(pair[1] for pair in pairs)
    if baseline <= 0:
        raise ValueError("Référence climatologique invalide")
    return 1 - model / baseline


def evaluate(rows: list[dict], meta: dict) -> dict:
    validate_manifest(meta)
    if len({row["year"] for row in rows}) != len(rows):
        raise ValueError("Années dupliquées")
    report = {
        "schema": "avantemps.verification-report.v1",
        "status": "insufficient_data",
        "publication_authorized": False,
        "scientific_review": "not_performed",
        "territory_id": meta["territory_id"],
        "forecast_system": meta["forecast_system"],
        "system_version": meta["system_version"],
        "initialization_month": meta["initialization_month"],
        "lead_month": meta["lead_month"],
        "n_distinct_years": len(rows),
        "minimum_years": MIN_YEARS,
        "reference": "equiprobable climatology (1/3 each)",
        "method": "RPS on LOYO observed terciles; paired yearly bootstrap",
        "limitations": (
            "Exploratoire. Métadonnées déclaratives ; vérifier les hindcasts, "
            "leur croisement avec les observations, les biais et les grilles. "
            "Aucune prévision ni alerte n'est autorisée."
        ),
        "skill": None,
    }
    if len(rows) < MIN_YEARS:
        return report
    categories = observed_categories(rows)
    pairs = [(rps(row["p"], category), rps((1/3, 1/3, 1/3), category))
             for row, category in zip(rows, categories)]
    estimate = skill(pairs)
    rng = random.Random(SEED)
    n = len(pairs)
    bootstrap = sorted(skill([pairs[rng.randrange(n)] for _ in range(n)])
                       for _ in range(N_BOOTSTRAPS))
    lower, upper = bootstrap[int(0.025*N_BOOTSTRAPS)], bootstrap[int(0.975*N_BOOTSTRAPS)-1]
    report["status"] = "exploratory_only"
    report["skill"] = {
        "name": "RPSS",
        "rps_model": round(statistics.fmean(p[0] for p in pairs), 6),
        "rps_climatology": round(statistics.fmean(p[1] for p in pairs), 6),
        "value": round(estimate, 6),
        "bootstrap_percentile_95": [round(lower, 6), round(upper, 6)],
        "bootstrap_replicates": N_BOOTSTRAPS,
        "note": "intervalle exploratoire positif" if lower > 0 else "gain non démontré",
    }
    return report


def run(manifest: Path, pairs: Path) -> dict:
    meta_bytes, pairs_bytes = manifest.read_bytes(), pairs.read_bytes()
    if len(meta_bytes) > 32768 or len(pairs_bytes) > MAX_CSV_BYTES:
        raise ValueError("Fichier d'entrée trop volumineux")
    meta = validate_manifest(json.loads(meta_bytes.decode("utf-8")))
    rows = parse_pairs(pairs_bytes.decode("utf-8-sig"), meta)
    report = evaluate(rows, meta)
    report["input_sha256"] = {
        "manifest": hashlib.sha256(meta_bytes).hexdigest(),
        "pairs": hashlib.sha256(pairs_bytes).hexdigest(),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="AVANTEMPS — vérification rétrospective expérimentale")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pairs", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.manifest, args.pairs)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(2, f"Évaluation refusée : {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
