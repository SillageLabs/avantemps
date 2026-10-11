# Vérifier les prévisions saisonnières — banc expérimental v0.1

Date : 11 octobre 2026. **Aucune performance régionale réelle n'a encore été calculée ou validée.**

## Justification

Une corrélation historique entre El Niño et la pluie ne suffit pas pour prévoir une saison. Les prévisions saisonnières sont probabilistes, et leurs performances dépendent du modèle, du lieu, de la saison et de l'échéance. Copernicus C3S fournit des prévisions rétrospectives appelées hindcasts. La période commune à de nombreux systèmes est 1993–2016, mais chaque système et version possède ses propres disponibilités.

### Documentation scientifique utilisée

- ECMWF, C3S seasonal forecasts : https://www.ecmwf.int/en/forecasts/datasets/c3s-seasonal-forecasts
- Tutoriel officiel de vérification C3S : https://ecmwf-training.github.io/c3s-training/submodules/c3s-training-submodule-seasonal-forecast/sf-verification/
- Description des graphiques de vérification C3S : https://confluence.ecmwf.int/spaces/CKB/pages/320997052/C3S+seasonal+forecasts+verification+plots
- Méthodologie WMO / ECMWF : https://confluence.ecmwf.int/spaces/WLS/pages/394992254/Verification
- Catalogue de statistiques mensuelles saisonnières : https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels

## Ce que calcule le code

Le banc v0.1 mesure uniquement la pertinence **exploratoire** de probabilités trois catégories : cumuls de pluie sur trois mois sous la normale / proches de la normale / au-dessus de la normale. On compare **un territoire, un modèle et sa version, un mois initial et un horizon** à la fois. Un score n'est produit qu'avec au moins vingt années calendaires distinctes et toutes les années de la période déclarée présentes. Cela ne démontre pas leur indépendance statistique.

Chaque paire a une année, trois probabilités dont la somme vaut 1 et un cumul de précipitations observé en millimètres. Les catégories observées sont calculées sur les *autres années uniquement* pour éviter qu'une année testée influence ses propres seuils (leave-one-year-out).

- RPS : moyenne des écarts quadratiques sur deux probabilités cumulées, catégories ordonnées.
- RPSS : 1 - RPS(model) / RPS(climatologie équiprobable 1/3, 1/3, 1/3). Une valeur <= 0 n'indique pas de gain.
- Intervalle bootstrap : mille tirages déterministes avec rééchantillonnage annuel, à titre exploratoire uniquement.

Les probabilités des modèles doivent elles-mêmes avoir été produites **sans utiliser l'année testée**, et sans sélectionner ex post le modèle gagnant. Le manifeste doit **déclarer** cette propriété, mais l'outil ne peut pas la prouver : un audit scientifique indépendant est impératif.

## Préparer deux fichiers locaux

Manifest JSON : exemple **structurel**, les identifiants doivent être remplacés par des informations réelles et contrôlées lors de l'étude.

~~~json
{
  "schema": "avantemps.hindcast.v1",
  "dataset_kind": "retrospective_hindcast_pairs",
  "territory_id": "nouvelle-caledonie",
  "variable": "total_precipitation_mm",
  "forecast_system": "CENTRE_ET_MODELE_PRECIS",
  "system_version": "VERSION",
  "spatial_method": "METHODE_D_EXTRACTION_ET_REPRESENTATIVITE",
  "forecast_tercile_method": "METHODE_DE_PROBABILITES_HORS_ANNEE",
  "observation_source_name": "REFERENCE_OBSERVATIONNELLE",
  "forecast_source_url": "https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels",
  "observation_source_url": "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-monthly-means",
  "initialization_month": 1,
  "lead_month": 2,
  "target_window_months": 3,
  "start_year": 1993,
  "end_year": 2016,
  "cross_validation_declaration": "leave_one_year_out"
}
~~~

CSV : structure, **ne pas utiliser ces nombres illustratifs comme données climatiques** :

~~~text
year,p_below,p_near,p_above,observed_mm
1993,0.25,0.45,0.30,120.0
1994,0.15,0.55,0.30,95.0
...
~~~

Le CSV doit contenir une vraie paire prévision-observation par année et uniquement une même combinaison (modèle/version, mois d'initialisation, horizon, territoire). Il ne doit **pas** être construit en mélangeant plusieurs échéances ou systèmes.

Commande hors ligne à la racine du dépôt :

~~~sh
python3 -m avantemps.verification --manifest ./manifest.json --pairs ./pairs.csv
~~~

Le résultat JSON contient aussi les empreintes SHA-256 des deux fichiers d'entrée, pour en documenter exactement les versions. Il est imprimé en console. Aucun fichier n'est écrit ni aucune donnée chiffrée publiée via l'API. Le champ publication_authorized est **toujours faux**, même si le RPSS est positif.

## Limitations de sécurité scientifique

1. **Couverture spatiale** : les produits C3S distribués à 1° × 1° ne sont pas des prévisions à l'échelle d'une commune ou d'une vallée ; la topographie locale importe en Nouvelle-Calédonie.
2. **Observations** : ERA5 à maille large n'est pas une station de pluie locale ; le choix du référentiel doit être documenté.
3. **Validation** : vingt années distinctes constituent seulement un seuil exploratoire d'utilisation du code, pas une garantie d'indépendance, de puissance statistique ou de validité des prédictions.
4. **Échantillons dépendants, multiplicité des essais, biais, dispersion** : le bootstrap de base ne les corrige pas automatiquement.
5. **Provenance et licence** : la présence d'une URL et d'une déclaration de validation croisée n'atteste ni l'origine réelle ni le droit de redistribution.
6. **Aucune activation automatique** : ni probabilité locale publiée, ni alerte, ni classement de risque issu de ce module.

Décision pour le produit : **qualité de prévision territoriale non évaluée** tant qu'aucun jeu de données officiel n'a été acquis et relu par un expert.


## Complétude de la période — correction du 11 octobre 2026

Le banc exige une paire par année sur toute la période déclarée dans le manifeste.
Une période 1993–2016 avec seulement vingt à vingt-trois années ne produit aucun
score : `status=incomplete_period`, `skill=null`, `missing_years` explicite.
Sous vingt années, `insufficient_data` reste prioritaire ; la liste des absences
est également fournie. Aucun remplissage ou exclusion silencieuse.

Une période plus courte, définie avant l'analyse et entièrement couverte, reste
évaluable si elle atteint vingt années. Ne pas modifier ex post la période pour
éliminer les années défavorables : la provenance et la justification doivent être
auditées. Cette règle de complétude est un garde-fou AVANTEMPS, pas une preuve
que vingt années suffisent scientifiquement ni une obligation attribuée à WMO.

Les appels Python directs `evaluate` vérifient aussi années, trois probabilités,
somme et précipitations finies/non négatives, sans dépendre d'un import CSV préalable.
Tests exclusivement SYNTHÉTIQUES : trous de période, vingt années sur vingt-quatre,
période déclarée complète de vingt ans et entrées invalides par appel direct.
Aucune compétence réelle mesurée ; accès CDS et revue scientifique restent requis.
