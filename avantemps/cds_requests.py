"""Planifier des extractions C3S hindcasts / ERA5 à faible emprise spatiale.

AUCUN accès réseau par défaut. Télécharger nécessite --execute, cdsapi et
l'acceptation préalable des licences dans le portail CDS (action utilisateur).
Les produits bruts ne sont jamais versionnés dans Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

FORECAST_DATASET = "seasonal-monthly-single-levels"
OBS_DATASET = "reanalysis-era5-single-levels-monthly-means"
NC_AREA = [-19, 163, -23, 169]  # Nord, Ouest, Sud, Est ; étude de grille, pas prévision locale
DOC_URL = "https://ecmwf-training.github.io/c3s-training/submodules/c3s-training-submodule-seasonal-forecast/sf-verification/"
SUPPORTED = {("ecmwf", "5")}  # Exemple SEAS5 explicitement documenté, autres systèmes après vérification


def shifted_month(year: int, month: int, months: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + months
    return index // 12, index % 12 + 1


def months_for_window(year: int, init_month: int, lead_month: int) -> list[tuple[int, int]]:
    # CDS seasonal monthly: leadtime_month=1 correspond au mois nominal d'initialisation.
    return [shifted_month(year, init_month, lead_month - 1 + offset)
            for offset in range(3)]


def plan(centre: str, system: str, first: int, last: int,
         init_month: int, lead_month: int) -> dict:
    if (centre, system) not in SUPPORTED:
        raise ValueError("Combinaison modèle/version non vérifiée : seul ecmwf system 5 est documenté")
    if type(first) is not int or type(last) is not int or not (1993 <= first <= last <= 2016):
        raise ValueError("Période de référence attendue entre 1993 et 2016")
    if type(init_month) is not int or not 1 <= init_month <= 12:
        raise ValueError("Mois d'initialisation incorrect")
    if type(lead_month) is not int or not 1 <= lead_month <= 4:
        raise ValueError("Fenêtre trimestrielle incompatible avec six mois de lead")
    if last - first + 1 < 20:
        raise ValueError("Moins de 20 années : pas assez pour le banc RPSS exploratoire")
    window = sorted({m for year in range(first, last+1)
                     for m in months_for_window(year, init_month, lead_month)})
    observation_years = sorted({str(y) for y, m in window})
    observation_months = sorted({f"{m:02d}" for y, m in window})
    forecast_request = {
        "data_format": "grib",
        "originating_centre": centre,
        "system": system,
        "variable": ["total_precipitation"],
        "product_type": "monthly_mean",
        "year": [str(y) for y in range(first, last+1)],
        "month": f"{init_month:02d}",
        "leadtime_month": [str(m) for m in range(lead_month, lead_month + 3)],
        "area": NC_AREA,
    }
    observation_request = {
        "product_type": "monthly_averaged_reanalysis",
        "variable": ["total_precipitation"],
        "year": observation_years,
        "month": observation_months,
        "time": "00:00",
        "grid": "1/1",
        "area": NC_AREA,
        "data_format": "grib",
    }
    return {
        "schema": "avantemps.cds-request-plan.v1",
        "execution": "not_performed",
        "publication_authorized": False,
        "territory_id": "nouvelle-caledonie",
        "area_nwse": NC_AREA,
        "centre": centre, "system": system,
        "first_year": first, "last_year": last,
        "init_month": init_month, "lead_month": lead_month,
        "target_window_months": 3,
        "forecast": {"dataset": FORECAST_DATASET, "request": forecast_request,
                     "documentation": "https://cds.climate.copernicus.eu/datasets/" + FORECAST_DATASET},
        "observations": {"dataset": OBS_DATASET, "request": observation_request,
                         "documentation": "https://cds.climate.copernicus.eu/datasets/" + OBS_DATASET},
        "notes": [
            "ERA5 : mois supplémentaires pour fenêtre traversant le changement d'année.",
            "La requête ERA5 peut renvoyer des mois supplémentaires : les filtrer à la conversion.",
            "Les échelles 1 degré ne représentent pas la pluie communale.",
            "Les conditions CDS doivent être acceptées avant téléchargement.",
            "L'option area devra être revérifiée dans l'interface CDS avant tout job réel.",
        ],
    }


def validate_plan(plan_obj: dict) -> None:
    """Reject altered requests before any CDS client or filesystem write."""
    if not isinstance(plan_obj, dict):
        raise ValueError("Plan CDS invalide")
    try:
        canonical = plan(plan_obj["centre"], plan_obj["system"],
                         plan_obj["first_year"], plan_obj["last_year"],
                         plan_obj["init_month"], plan_obj["lead_month"])
    except (KeyError, TypeError) as exc:
        raise ValueError("Plan CDS incomplet ou malformé") from exc
    # JSON serialization also distinguishes False from 0 and True from 1.
    if json.dumps(plan_obj, sort_keys=True) != json.dumps(canonical, sort_keys=True):
        raise ValueError("Plan CDS modifié : regénérer le plan officiel")


def _safe_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def download(plan_obj: dict, output_dir: Path) -> dict:
    """Opération explicite et non silencieuse. Jamais appelée par l'API/CI."""
    validate_plan(plan_obj)
    try:
        import cdsapi
    except ImportError as exc:
        raise RuntimeError("Installer cdsapi dans un environnement séparé, puis configurer ~/.cdsapirc") from exc
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Le répertoire de sortie doit être vide pour éviter les écrasements")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": "avantemps.cds-download-manifest.v1",
                "plan": plan_obj, "artifacts": [],
                "downloaded_at_utc": None, "publication_authorized": False}
    client = cdsapi.Client()
    for key in ("forecast", "observations"):
        entry = plan_obj[key]
        target = output_dir / (key + ".grib")
        print(f"[CDS] Téléchargement {key}: {entry['dataset']} -> {target}", flush=True)
        client.retrieve(entry["dataset"], entry["request"], str(target))
        if not target.is_file() or target.stat().st_size < 100:
            raise ValueError(f"Le fournisseur n'a pas créé un fichier exploitable pour {key}")
        with target.open("rb") as stream:
            first_bytes = stream.read(4)
            stream.seek(-4, 2)
            last_bytes = stream.read(4)
        if first_bytes != b"GRIB" or last_bytes != b"7777":
            raise ValueError(f"Réponse CDS non GRIB ou possiblement archive ZIP pour {key} : inspecter le téléchargement")
        digest = hashlib.sha256()
        with target.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        file_size = target.stat().st_size
        manifest["artifacts"].append({
            "role": key, "dataset": entry["dataset"],
            "filename": target.name,
            "bytes": file_size,
            "sha256": digest.hexdigest(),
        })
        print(f"[CDS] {key}: {file_size:,} octets, SHA256 {digest.hexdigest()}", flush=True)
    manifest["downloaded_at_utc"] = datetime.now(timezone.utc).isoformat()
    _safe_write(output_dir / "download-manifest.json",
                (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan CDS + extraction seulement sur --execute")
    parser.add_argument("--centre", default="ecmwf")
    parser.add_argument("--system", default="5")
    parser.add_argument("--first-year", type=int, default=1993)
    parser.add_argument("--last-year", type=int, default=2016)
    parser.add_argument("--init-month", type=int, default=9)
    parser.add_argument("--lead-month", type=int, default=1)
    parser.add_argument("--execute", action="store_true", help="Lance réellement deux téléchargements CDS")
    parser.add_argument("--acknowledge-cds-terms", action="store_true",
                        help="Confirme que vous avez accepté les licences dans votre compte CDS")
    parser.add_argument("--output-dir", type=Path, default=Path("var/cds-nc"))
    args = parser.parse_args()
    try:
        req = plan(args.centre, args.system, args.first_year, args.last_year,
                   args.init_month, args.lead_month)
        if args.execute:
            if not args.acknowledge_cds_terms:
                parser.error("--execute exige --acknowledge-cds-terms")
            result = download(req, args.output_dir)
            print(json.dumps({"status": "downloaded_for_local_research", "artifacts": result["artifacts"],
                              "publication_authorized": False}, indent=2))
        else:
            print(json.dumps(req, ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(2, f"Échec : {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
