"""Lecture stricte du fichier RONI officiel NOAA/CPC.

RONI est une observation climatique ; ce n'est pas une alerte locale.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

SOURCE_URL = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"
EXPLANATION_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/"
SEASONS = ("DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ")
ORDER = {name: i for i, name in enumerate(SEASONS)}


@dataclass(frozen=True)
class Record:
    season: str
    year: int
    anomaly_c: float

    def json(self) -> dict:
        return asdict(self)


def signal(value: float) -> str:
    """Simple zone numérique, jamais un diagnostic ENSO officiel."""
    if value > 0.5:
        return "warm_index"
    if value < -0.5:
        return "cold_index"
    return "neutral_index"


def parse_roni(text: str) -> list[Record]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0].split() != ["SEAS", "YR", "ANOM"]:
        raise ValueError("En-tête RONI invalide (SEAS YR ANOM attendu)")
    records: list[Record] = []
    previous: int | None = None
    for number, line in enumerate(lines[1:], 2):
        fields = line.split()
        if len(fields) != 3:
            raise ValueError(f"Ligne {number}: trois colonnes attendues")
        season, year_s, anomaly_s = fields
        if season not in ORDER:
            raise ValueError(f"Ligne {number}: saison inconnue {season!r}")
        try:
            year = int(year_s)
            anomaly = float(anomaly_s)
        except ValueError as exc:
            raise ValueError(f"Ligne {number}: valeur invalide") from exc
        if not (1900 <= year <= 2200 and math.isfinite(anomaly) and -10 <= anomaly <= 10):
            raise ValueError(f"Ligne {number}: valeur hors limites")
        number_in_series = year * 12 + ORDER[season]
        if previous is not None and number_in_series != previous + 1:
            raise ValueError(f"Ligne {number}: doublon, saison manquante ou ordre invalide")
        previous = number_in_series
        records.append(Record(season, year, anomaly))
    if not records:
        raise ValueError("Aucune observation RONI")
    return records


def validate_noaa_history(records: list[Record]) -> None:
    """Le produit NOAA utilisé en 2026 commence en DJF 1950.

    Un extrait cohérent, mais tronqué, ne doit pas être publié comme archive complète.
    """
    if (
        len(records) < 840
        or records[0].year != 1950
        or records[0].season != "DJF"
        or records[-1].year < 2020
    ):
        raise ValueError("Historique NOAA incomplet ou anormalement tronqué")


def latest_summary(records: list[Record]) -> dict:
    if not records:
        raise ValueError("Aucune observation")
    last = records[-1]
    previous = records[-2] if len(records) > 1 else None
    return {
        "latest": last.json(),
        "signal": signal(last.anomaly_c),
        "previous": previous.json() if previous else None,
        "delta_from_previous_c": round(last.anomaly_c - previous.anomaly_c, 2) if previous else None,
        "observation_count": len(records),
        "interpretation": (
            "Le RONI seul ne confirme pas un épisode ENSO et ne prédit pas "
            "de catastrophe locale. Les dernières observations peuvent être révisées."
        ),
    }
