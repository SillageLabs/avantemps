"""Analyse stricte du fichier officiel NOAA/CPC RONI.ascii.txt.

Le RONI est une observation climatique, pas une alerte ni une prédiction locale.
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
    """Indication de l'indice seulement, PAS une phase ENSO confirmée."""
    if value > 0.5:
        return "warm_index"
    if value < -0.5:
        return "cold_index"
    return "neutral_index"


def parse_roni(text: str) -> list[Record]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines or lines[0].split() != ["SEAS", "YR", "ANOM"]:
        raise ValueError("En-tête NOAA RONI inattendu (SEAS YR ANOM requis)")
    records: list[Record] = []
    previous: tuple[int, int] | None = None
    for number, line in enumerate(lines[1:], 2):
        columns = line.split()
        if len(columns) != 3:
            raise ValueError(f"Ligne {number} : trois colonnes attendues")
        season, year_text, anomaly_text = columns
        if season not in ORDER:
            raise ValueError(f"Ligne {number} : saison inconnue {season!r}")
        try:
            year = int(year_text)
            anomaly = float(anomaly_text)
        except ValueError as exc:
            raise ValueError(f"Ligne {number} : valeur invalide") from exc
        if not (1900 <= year <= 2200 and math.isfinite(anomaly) and -10 <= anomaly <= 10):
            raise ValueError(f"Ligne {number} : valeur hors limites")
        key = (year, ORDER[season])
        if previous is not None and key <= previous:
            raise ValueError(f"Ligne {number} : doublon ou ordre chronologique invalide")
        previous = key
        records.append(Record(season, year, anomaly))
    if not records:
        raise ValueError("Le fichier NOAA ne contient aucune observation")
    return records


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
            "Le signal RONI n'est pas une confirmation d'épisode ENSO et ne "
            "permet pas de prédire une catastrophe locale. Les observations "
            "récentes peuvent être révisées par la NOAA."
        ),
    }
