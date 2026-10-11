"""Apparier des séries mensuelles pré-extraites et calculer des probabilités hors année cible.

ATTENTION : entrées CSV de grille déjà sélectionnée et inspectée dans les GRIB.
L'origine et la représentativité géographique doivent être vérifiées séparément.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import io
import json
import math
from pathlib import Path

from .cds_requests import plan as create_plan, months_for_window
from .verification import quantile, parse_pairs, validate_manifest

F_COLS = ["year", "member", "lead_month", "tp_m_per_s"]
O_COLS = ["year", "month", "tp_m_per_day"]
MAX_FILE_BYTES = 2_000_000


def month_days(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def m_s_to_mm_month(value: float, year: int, month: int) -> float:
    if not (math.isfinite(value) and value >= 0):
        raise ValueError("Taux de pluie saisonnière invalide")
    return value * month_days(year, month) * 86400 * 1000


def m_day_to_mm_month(value: float, year: int, month: int) -> float:
    if not (math.isfinite(value) and value >= 0):
        raise ValueError("Pluie mensuelle ERA5 invalide")
    return value * month_days(year, month) * 1000


def _parse_csv(content: str, required: list[str]) -> list[dict]:
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("Entrée CSV trop volumineuse")
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames != required:
        raise ValueError("Colonnes CSV attendues : " + ",".join(required))
    rows = []
    for row in reader:
        if None in row or any(x is None or not x.strip() for x in row.values()):
            raise ValueError("Ligne CSV incomplète")
        rows.append(row)
    if not rows:
        raise ValueError("CSV vide")
    return rows


def _float(text: str) -> float:
    try:
        number = float(text)
    except ValueError as exc:
        raise ValueError("Nombre décimal invalide") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError("Pluie négative ou non finie")
    return number


def _year(value: str, lo: int, hi: int) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError("Année invalide") from exc
    if not (lo <= parsed <= hi):
        raise ValueError("Année hors période")
    return parsed


def pair_from_monthlies(request_plan: dict, forecasts: str, observations: str) -> tuple[str, dict]:
    if request_plan.get("schema") != "avantemps.cds-request-plan.v1":
        raise ValueError("Plan CDS invalide")
    canonical = create_plan(
        request_plan["centre"], request_plan["system"],
        request_plan["first_year"], request_plan["last_year"],
        request_plan["init_month"], request_plan["lead_month"],
    )
    if request_plan != canonical:
        raise ValueError("Plan modifié : regénérer le plan officiel")
    init_month = request_plan["init_month"]
    lead = request_plan["lead_month"]
    years = list(range(request_plan["first_year"], request_plan["last_year"] + 1))
    f_rows = _parse_csv(forecasts, F_COLS)
    o_rows = _parse_csv(observations, O_COLS)
    forecast_data: dict[tuple[int, str, int], float] = {}
    members = set()
    for row in f_rows:
        year = _year(row["year"], years[0], years[-1])
        member = row["member"].strip()
        if not member.isdigit() or not 0 <= int(member) < 200:
            raise ValueError("Identifiant membre de prévision invalide")
        try:
            lead_month = int(row["lead_month"])
        except ValueError as exc:
            raise ValueError("Lead mensuel invalide") from exc
        if not lead <= lead_month < lead + 3:
            raise ValueError("Lead hors fenêtre demandée")
        key = (year, member, lead_month)
        if key in forecast_data:
            raise ValueError("Membre/année/lead dupliqué")
        members.add(member)
        cal_year, cal_month = months_for_window(year, init_month, lead)[lead_month - lead]
        forecast_data[key] = m_s_to_mm_month(_float(row["tp_m_per_s"]), cal_year, cal_month)
    if not (2 <= len(members) <= 199):
        raise ValueError("Nombre de membres insuffisant ou anormal")
    observed: dict[tuple[int, int], float] = {}
    for row in o_rows:
        year = _year(row["year"], years[0], years[-1]+1)
        try:
            month = int(row["month"])
        except ValueError as exc:
            raise ValueError("Mois d'observation invalide") from exc
        if not 1 <= month <= 12:
            raise ValueError("Mois d'observation hors 1-12")
        key = (year, month)
        if key in observed:
            raise ValueError("Mois d'observation dupliqué")
        observed[key] = m_day_to_mm_month(_float(row["tp_m_per_day"]), year, month)
    seasonal_forecasts: dict[int, list[float]] = {}
    seasonal_obs: dict[int, float] = {}
    for year in years:
        window = months_for_window(year, init_month, lead)
        if any(key not in observed for key in window):
            raise ValueError(f"Observation manquante en {year} (incluant changement d'année)")
        seasonal_obs[year] = sum(observed[key] for key in window)
        member_totals = []
        for member in sorted(members, key=int):
            keys = [(year, member, lm) for lm in range(lead, lead + 3)]
            if any(key not in forecast_data for key in keys):
                raise ValueError(f"Prévision incomplète en {year} pour le membre {member}")
            member_totals.append(sum(forecast_data[key] for key in keys))
        seasonal_forecasts[year] = member_totals
    lines = [",".join(["year", "p_below", "p_near", "p_above", "observed_mm"])]
    for year in years:
        train = sorted(value for other_year in years if other_year != year
                       for value in seasonal_forecasts[other_year])
        low, high = quantile(train, 1 / 3), quantile(train, 2 / 3)
        if low >= high:
            raise ValueError("Terciles modèles non discriminants")
        totals = seasonal_forecasts[year]
        below = sum(total < low for total in totals)
        above = sum(total > high for total in totals)
        middle = len(totals) - below - above
        counts = (below / len(totals), middle / len(totals), above / len(totals))
        lines.append(",".join([str(year)] + [format(value, ".15g") for value in counts] +
                              [format(seasonal_obs[year], ".15g")]))
    csv_text = "\n".join(lines) + "\n"
    metadata = {
        "schema": "avantemps.hindcast.v1",
        "dataset_kind": "retrospective_hindcast_pairs",
        "territory_id": "nouvelle-caledonie",
        "variable": "total_precipitation_mm",
        "forecast_system": request_plan["centre"],
        "system_version": request_plan["system"],
        "spatial_method": "ONE_GRIDPOINT_EXPERIMENT__EXTRACTION_MUST_BE_AUDITED",
        "forecast_tercile_method": "ensemble member 3-month totals; leave-one-year-out thresholds",
        "observation_source_name": "ERA5 gridpoint monthly reanalysis; not local rain gauges",
        "forecast_source_url": request_plan["forecast"]["documentation"],
        "observation_source_url": request_plan["observations"]["documentation"],
        "initialization_month": init_month,
        "lead_month": lead,
        "target_window_months": 3,
        "start_year": years[0], "end_year": years[-1],
        "cross_validation_declaration": "leave_one_year_out",
    }
    validate_manifest(metadata)
    parse_pairs(csv_text, metadata)
    provenance = {
        "schema": "avantemps.pairing-provenance.v1",
        "publication_authorized": False,
        "extraction_verified": False,
        "land_mask_verified": False,
        "forecast_members": len(members),
        "years": len(years),
        "source_csv_sha256": {
            "forecast": hashlib.sha256(forecasts.encode("utf-8")).hexdigest(),
            "observations": hashlib.sha256(observations.encode("utf-8")).hexdigest(),
        },
        "unit_handling": {
            "seasonal_forecast": "m/s * days_in_valid_month * 86400 * 1000",
            "ERA5_monthly": "m/day * days_in_month * 1000",
        },
        "warning": "CSV préparés depuis GRIB à vérifier séparément. Résultat exploratoire interdit de publication.",
    }
    return csv_text, {"manifest": metadata, "provenance": provenance}


def main() -> int:
    parser = argparse.ArgumentParser(description="Conversion de CSV mensuels préparés vers pairs.csv hors ligne")
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--forecast-monthly", required=True, type=Path)
    parser.add_argument("--observed-monthly", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        payloads = [path.read_bytes() for path in
                    (args.plan, args.forecast_monthly, args.observed_monthly)]
        if any(len(raw) > MAX_FILE_BYTES for raw in payloads):
            raise ValueError("Entrée trop volumineuse")
        request_plan = json.loads(payloads[0].decode("utf-8"))
        csv_text, report = pair_from_monthlies(request_plan, payloads[1].decode("utf-8-sig"),
                                               payloads[2].decode("utf-8-sig"))
        out = args.output_dir
        if out.exists() and any(out.iterdir()):
            raise ValueError("Répertoire de sortie non vide : aucun écrasement permis")
        out.mkdir(parents=True, exist_ok=True)
        for name, content in (
            ("pairs.csv", csv_text),
            ("manifest.json", json.dumps(report["manifest"], ensure_ascii=False, indent=2)+"\n"),
            ("provenance.json", json.dumps(report["provenance"], ensure_ascii=False, indent=2)+"\n"),
        ):
            (out / name).write_text(content, encoding="utf-8")
        print(f"Préparation terminée : {out} — NON destinée à publication", flush=True)
    except (OSError, ValueError, KeyError, UnicodeError, TypeError) as exc:
        parser.exit(2, f"Préparation refusée : {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
