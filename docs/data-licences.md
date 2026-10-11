# Revue des licences de données — 11 octobre 2026

Revue documentaire pour les tickets #6 et #10. Aucun fichier Copernicus ou série
de station locale n'a été téléchargé dans cette livraison. Les conditions
ci-dessous ont été lues sur les sources officielles ; elles ne constituent pas
une preuve que le titulaire du compte a accepté les licences dans CDS.

## État des sources du protocole d'acquisition

| Source | Conditions observées | Attribution et transformations | État AVANTEMPS |
| --- | --- | --- | --- |
| C3S seasonal monthly single levels | La fiche affiche CC-BY et une licence additionnelle pour contributions non européennes | Citer le jeu, sa source, sa licence ; documenter les transformations | Requêtes préparées, aucune donnée réelle acquise |
| ERA5 monthly averaged single levels | La fiche affiche CC-BY | Citer le jeu et la licence ; distinguer réanalyse et mesures locales | Requête préparée, aucune donnée réelle acquise |
| Contributions C3S de centres non européens | Texte additionnel : utilisation/redistribution permises, reconnaissance de la source originale, absence de garantie de continuité/qualité et de responsabilité du centre | Conserver le centre d'origine dans toute communication | Aucun élargissement du protocole ECMWF à ces centres |
| Stations de Nouvelle-Calédonie | Aucune licence précise d'un jeu identifié n'a pu être établie dans cette revue | À vérifier sur la fiche du jeu et ses conditions effectives | Acquisition et redistribution non validées |

### Sources primaires consultées

1. Fiche C3S : https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels?tab=overview — DOI `10.24381/cds.68dd14c3`.
2. Fiche ERA5 mensuel : https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-monthly-means?tab=overview — DOI `10.24381/cds.f17050d7`.
3. Licence CDS CC-BY, révision 1 : https://cds.climate.copernicus.eu/licences/cc-by.
4. Texte lié par cette page : https://creativecommons.org/licenses/by/4.0/legalcode.
5. Conditions additionnelles, révision 1 : https://cds.climate.copernicus.eu/licences/Additional-licence-to-use-non-European-contributions.
6. Accès CDS et acceptation manuelle : https://cds.climate.copernicus.eu/how-to-api.
7. Page locale actuelle consultée : https://meteo.nc/fr/donnees-publiques.

La licence CC-BY 4.0 permet le partage et l'adaptation, y compris commerciaux,
sous ses conditions d'attribution : conserver les mentions fournies applicables,
identifier la licence avec un lien et signaler les modifications. Ne pas suggérer
un soutien du producteur à AVANTEMPS. Lire le texte complet avant redistribution.

Le texte additionnel vise les centres non européens ; il ne transforme pas les
sorties de modèles en observations de terrain et n'apporte aucune garantie
scientifique. Les licences de données sont distinctes de la licence du code.

## Préparer l'acquisition légitime

L'API CDS exige que les conditions du jeu soient acceptées manuellement sur sa
page de téléchargement. Le marqueur CLI `--acknowledge-cds-terms` est seulement
une déclaration de l'opérateur. Aucun manifeste ou SHA-256 ne certifie cette
acceptation. Ne stocker aucune clé CDS ni fichier `.cdsapirc` dans Git.

Au moment d'une acquisition réelle, conserver localement : fiche du jeu et DOI,
URL/révision de licence visible, date de consultation et d'acceptation déclarée,
requête exacte, date de collecte, version du système et empreintes des fichiers.
Le manifeste actuel couvre requêtes/date/empreintes ; les preuves documentaires
de licence doivent être conservées séparément. Pas de faux justificatif généré.

Pour chaque export dérivé, renseigner la source, le système, la période, le
protocole spatial, les unités et les opérations réellement effectuées : sélection,
regrillage, agrégation, conversion et calibration. Ne déclarer aucune opération
avant son exécution. Les transformations AVANTEMPS ne sont pas des produits
validés ou approuvés par ECMWF/Copernicus.

## Blocage des données locales

La page publique locale consultée ne fournit pas de fiche de séries de stations
avec licence exploitable. D'anciens documents apparaissent dans la recherche,
mais leur applicabilité actuelle n'est pas établie. On ne déduit pas les droits
des stations calédoniennes des conditions d'un autre portail Météo-France.

Il reste à identifier un jeu couvrant la période et les stations pertinentes,
sa licence actuelle, ses droits de redistribution, sa qualité et sa complétude.
Aucune demande, inscription payante ou commande de données n'a été effectuée.

## Limites et décisions restantes

- Accès personnel CDS et acceptation des conditions des deux jeux nécessaires.
- Licence et accès aux observations de stations encore à établir.
- Licence du code AVANTEMPS à choisir séparément ; cette revue n'en attribue pas.
- Conservation/redistribution des séries locales à définir selon leurs conditions.
- Revue scientifique externe et autorisation de déploiement toujours nécessaires.

La vérification des marques, l'accessibilité, les entretiens utilisateurs et la
politique des sources périmées du ticket #6 restent hors de cette revue. Aucun
score, alerte, service public ou déploiement n'est autorisé par une licence seule.
