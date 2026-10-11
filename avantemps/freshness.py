"""Politique d'affichage interne ; aucune certification scientifique de fraîcheur."""
from __future__ import annotations

import calendar
from datetime import datetime, timezone

from .roni import ORDER

CHECK_MAX_DAYS = 45
OBSERVATION_MAX_DAYS = 90


def assess_freshness(snapshot: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Horloge avec fuseau obligatoire")
    now = now.astimezone(timezone.utc)
    result = {
        "policy": "avantemps.noaa-freshness.v1",
        "assessed_at_utc": now.isoformat(),
        "check_max_days": CHECK_MAX_DAYS,
        "observation_max_days": OBSERVATION_MAX_DAYS,
        "status": "unknown",
        "reasons": [],
        "message": "Fraîcheur indéterminée : consulter la source officielle et les dates de l'archive.",
    }
    try:
        # Ne pas remplacer une vérification manquante par la date de première collecte.
        checked = datetime.fromisoformat(snapshot["last_checked_at_utc"])
        if checked.tzinfo is None or checked.utcoffset() is None:
            raise ValueError("Date sans fuseau")
        checked = checked.astimezone(timezone.utc)
        latest = snapshot["summary"]["latest"]
        year = latest["year"]
        if type(year) is not int:
            raise ValueError("Année invalide")
        # NOAA attribue l'année au mois central : DJF 2026 finit en février,
        # NDJ 2026 finit en janvier 2027. On date la fin du dernier mois couvert.
        final_month = ORDER[latest["season"]] + 2
        if final_month == 13:
            year, final_month = year + 1, 1
        end = datetime(year, final_month, calendar.monthrange(year, final_month)[1],
                       tzinfo=timezone.utc)
        check_age = (now - checked).total_seconds() / 86400
        observation_age = (now.date() - end.date()).days
        if check_age < 0 or observation_age < 0:
            raise ValueError("Date future")
    except (KeyError, TypeError, ValueError, OverflowError):
        result["reasons"] = ["invalid_or_future_date"]
        return result
    result.update(check_age_days=round(check_age, 2), observation_age_days=observation_age,
                  observation_period_end=end.date().isoformat())
    reasons = []
    if check_age > CHECK_MAX_DAYS:
        reasons.append("source_not_checked_recently")
    if observation_age > OBSERVATION_MAX_DAYS:
        reasons.append("observation_too_old")
    result["reasons"] = reasons
    result["status"] = "stale" if reasons else "within_internal_limits"
    result["message"] = (
        "Archive ancienne ou source non vérifiée récemment : ces valeurs sont historiques ; consulter NOAA pour l'état actuel."
        if reasons else
        "Dates dans les limites internes du prototype ; observations révisables, sans garantie d'actualité de NOAA."
    )
    return result
