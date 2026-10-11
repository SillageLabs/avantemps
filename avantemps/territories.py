"""Dossiers territoriaux relus manuellement, séparés de l'indice RONI.

Ce module ne calcule ni risque, ni prévision locale, ni niveau d'alerte.
Chaque fait publié cite une source institutionnelle et sa date.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from urllib.parse import urlparse

SOURCES = {
    "mf_nc_climate_2025": {
        "publisher": "Météo-France Nouvelle-Calédonie",
        "title": "Le climat en Nouvelle-Calédonie",
        "published_on": "2025-12-09",
        "url": "https://meteo.nc/fr/node/569750",
    },
    "mf_nc_enso_2026": {
        "publisher": "Météo-France Nouvelle-Calédonie",
        "title": "Le phénomène ENSO (El Niño Southern Oscillation)",
        "published_on": "2026-09-29",
        "url": "https://meteo.nc/en/node/569807",
    },
    "mf_nc_outlook_2026": {
        "publisher": "Météo-France Nouvelle-Calédonie",
        "title": "Prévision saisonnière octobre–novembre–décembre 2026",
        "published_on": "2026-09-17",
        "url": "https://meteo.nc/en/node/569805",
    },
    "mf_nc_rain_2026": {
        "publisher": "Météo-France Nouvelle-Calédonie",
        "title": "Bulletin de suivi pluviométrique – septembre 2026",
        "published_on": "2026-10-06",
        "url": "https://meteo.nc/fr/publications/bulletin-de-suivi-pluviometrique-septembre-2026",
    },
}

PROFILES = {
    "nouvelle-caledonie": {
        "id": "nouvelle-caledonie",
        "name": "Nouvelle-Calédonie",
        "status": "documented_climatology",
        "reviewed_on": "2026-10-11",
        "intro": (
            "Les liens entre ENSO et les pluies sont étudiés en Nouvelle-Calédonie. "
            "Ces connaissances concernent des tendances historiques et ne constituent "
            "pas une prévision pour une commune."
        ),
        "climatology": [
            {
                "id": "nc_enso_precipitation",
                "kind": "documented_association",
                "subject": "Précipitations pendant El Niño",
                "detail": (
                    "Selon Météo-France Nouvelle-Calédonie, d'octobre à mars les "
                    "précipitations sont en moyenne environ 20 % plus faibles "
                    "qu'en phase ENSO neutre. Il s'agit d'une moyenne historique "
                    "et non d'un déficit prévu en 2026."
                ),
                "scope": "Nouvelle-Calédonie, octobre–mars, comparaison avec ENSO neutre",
                "source_ids": ["mf_nc_enso_2026"],
            },
            {
                "id": "nc_spatial_variation",
                "kind": "documented_association",
                "subject": "Effets géographiquement variables",
                "detail": (
                    "L'influence d'ENSO sur les précipitations est particulièrement "
                    "marquée en saison chaude, dans le nord de la Grande Terre et "
                    "sur les îles Loyauté. Le résultat local ne peut pas être "
                    "déduit d'un indice océanique global."
                ),
                "scope": "Climatologie régionale, pas commune par commune",
                "source_ids": ["mf_nc_climate_2025"],
            },
            {
                "id": "nc_drought_context",
                "kind": "documented_association",
                "subject": "Contexte des sécheresses",
                "detail": (
                    "Les épisodes El Niño s'accompagnent historiquement d'un "
                    "risque accru de sécheresse et de feux de végétation. "
                    "Ce constat ne signifie pas qu'un feu ou une sécheresse "
                    "soit annoncé à une date ou un endroit donné."
                ),
                "scope": "Lien climatologique, aucune alerte active",
                "source_ids": ["mf_nc_climate_2025", "mf_nc_enso_2026"],
            },
        ],
        "dated_publications": [
            {
                "id": "nc_outlook_2026_09",
                "kind": "dated_official_bulletin",
                "subject": "Bulletin saisonnier publié le 17 septembre 2026",
                "detail": (
                    "Dans son bulletin visant octobre à décembre 2026, "
                    "Météo-France indique qu'en septembre 2026 un épisode "
                    "El Niño est en phase croissante. Cette citation est "
                    "datée ; elle n'est pas actualisée automatiquement."
                ),
                "reference_period": "2026-10 à 2026-12",
                "source_ids": ["mf_nc_outlook_2026"],
            },
            {
                "id": "nc_rainfall_2026_09",
                "kind": "dated_observation",
                "subject": "Pluie observée en septembre 2026",
                "detail": (
                    "Le bulletin Météo-France publié le 6 octobre indique "
                    "20 mm de précipitations à l'échelle du territoire "
                    "en septembre, soit un déficit de 64 % selon son "
                    "bilan. L'attribution causale à ENSO n'est pas établie "
                    "par cette seule observation."
                ),
                "reference_period": "2026-09",
                "source_ids": ["mf_nc_rain_2026"],
            },
        ],
        "conclusion": (
            "Un lien climatologique documenté n'autorise pas un chiffre de risque "
            "local. Consulter Météo-France Nouvelle-Calédonie pour les prévisions "
            "actuelles et les consignes des autorités pour les situations dangereuses."
        ),
        "official_information_url": "https://meteo.nc/fr",
    },
    "nantes": {
        "id": "nantes",
        "name": "Nantes",
        "status": "not_assessed",
        "reviewed_on": "2026-10-11",
        "intro": (
            "Aucune étude territoriale ENSO validée n'a encore été intégrée "
            "à AVANTEMPS pour Nantes."
        ),
        "climatology": [],
        "dated_publications": [],
        "conclusion": (
            "AVANTEMPS s'abstient : une valeur RONI mondiale ne permet pas "
            "de conclure à un risque local. Utiliser les prévisions et vigilances "
            "officielles pour connaître la situation météorologique."
        ),
        "official_information_url": "https://meteofrance.com/",
    },
    "guyane": {
        "id": "guyane",
        "name": "Guyane",
        "status": "not_assessed",
        "reviewed_on": "2026-10-11",
        "intro": (
            "Une étude du rôle d'ENSO en Guyane est envisagée, "
            "mais aucune relation territoriale n'a encore été validée dans ce projet."
        ),
        "climatology": [],
        "dated_publications": [],
        "conclusion": (
            "AVANTEMPS s'abstient de toute prévision ou indice de risque "
            "pour la Guyane sans analyse régionale vérifiée."
        ),
        "official_information_url": "https://meteofrance.gf/",
    },
}

ALLOWED_KINDS = {
    "documented_association", "dated_official_bulletin", "dated_observation",
}
FORBIDDEN_FIELDS = {"risk_score", "alert_level", "probability", "local_forecast", "threat_level"}
ALLOWED_STATUSES = {"documented_climatology", "not_assessed"}


def validate_registry() -> None:
    for source in SOURCES.values():
        parsed = urlparse(source["url"])
        if parsed.scheme != "https" or parsed.hostname != "meteo.nc":
            raise ValueError("Source territoriale inattendue")
        date.fromisoformat(source["published_on"])
        if not source["title"] or not source["publisher"]:
            raise ValueError("Source sans attribution")
    for key, profile in PROFILES.items():
        if key != profile["id"] or profile["status"] not in ALLOWED_STATUSES:
            raise ValueError("Territoire ou statut invalide")
        date.fromisoformat(profile["reviewed_on"])
        if not profile["intro"] or not profile["conclusion"]:
            raise ValueError("Contexte / limite manquante")
        if FORBIDDEN_FIELDS.intersection(profile):
            raise ValueError("Score ou alerte non autorisés")
        entries = profile["climatology"] + profile["dated_publications"]
        if profile["status"] == "not_assessed" and entries:
            raise ValueError("Un territoire non évalué ne doit contenir aucune conclusion locale")
        for entry in entries:
            if FORBIDDEN_FIELDS.intersection(entry):
                raise ValueError("Score ou alerte non autorisés")
            if entry["kind"] not in ALLOWED_KINDS:
                raise ValueError("Nature de l'affirmation invalide")
            if not entry["source_ids"] or any(i not in SOURCES for i in entry["source_ids"]):
                raise ValueError("Une affirmation doit être sourcée")
            if not entry["subject"] or not entry["detail"]:
                raise ValueError("Affirmation vide")


def list_territories() -> list[dict]:
    return [
        {"id": value["id"], "name": value["name"],
         "status": value["status"], "reviewed_on": value["reviewed_on"]}
        for value in PROFILES.values()
    ]


def get_territory(territory_id: str) -> dict | None:
    if territory_id not in PROFILES:
        return None
    profile = deepcopy(PROFILES[territory_id])
    cited = {source_id for item in profile["climatology"] + profile["dated_publications"]
             for source_id in item["source_ids"]}
    profile["sources"] = {source_id: deepcopy(SOURCES[source_id]) for source_id in sorted(cited)}
    profile["disclaimer"] = (
        "Dossier documentaire daté, non mis à jour en direct. "
        "Ce produit n'émet aucune vigilance et ne calcule aucun risque local "
        "à partir de RONI."
    )
    return profile


validate_registry()
