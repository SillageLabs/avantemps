# Registre de sources et exigences de qualité

Dernière revue documentaire initiale : 2026-10-11. Les licences, quotas, conditions de redistribution et disponibilité sont **à revérifier avant mise en production**.

| Priorité | Source | Usage prévu | État |
| --- | --- | --- | --- |
| P0 | NOAA CPC RONI : https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt | Historique ENSO, saisons glissantes, versionnement | Intégré v0 |
| P0 | NOAA CPC RONI : https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/ | Définition, révisions possibles et limites | Documenté |
| P1 | NOAA CPC diagnostics ENSO : https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml | Confirmation scientifique de la phase ENSO | À étudier, **pas** inférée automatiquement |
| P1 | Copernicus C3S : https://cds.climate.copernicus.eu/datasets/seasonal-postprocessed-single-levels | Anomalies et prévisions saisonnières | Étude de faisabilité |
| P2 | GDACS : https://www.gdacs.org/ | Catastrophes détectées / remontées | Étude de faisabilité |
| P2 | Météo-France / data.gouv.fr : https://www.data.gouv.fr/dataservices/api-bulletin-vigilance | Vigilances françaises officielles | Étude de faisabilité |
| P2 | Vigicrues : https://www.vigicrues.gouv.fr/ | Informations de crues en France | Étude de faisabilité |
| P2 | WMO CAP : https://wmo.int/site/wmo-common-alerting-protocol/about-cap | Schéma des messages d'alerte | Étude de faisabilité |

## Pourquoi RONI plutôt que seulement ONI ?

Le Climate Prediction Center a fait de l'indice relatif RONI son indicateur opérationnel pour ENSO en 2026 ; l'ancien ONI reste utile comme série historique et complément. Ne jamais comparer directement RONI et ONI comme s'ils utilisaient la même définition.

Fichier officiel v0 : colonnes `SEAS YR ANOM`. La saison est un trimestre glissant labellisé (par exemple DJF), et la valeur est une anomalie en degrés Celsius. Le fichier n'est pas une prévision.

L'indice de référence est fondé sur ERSSTv6. **Les deux derniers mois de RONI peuvent être révisés**. Le code archive les versions brutes, et n'efface pas les précédentes.

Un signal > +0,5°C / < -0,5°C est indicatif des conditions océaniques relatives. La définition historique des *épisodes* implique au moins cinq saisons glissantes consécutives et une vérification de la cohérence océan-atmosphère. AVANTEMPS v0 **n'attribue jamais la phase ENSO officielle** à partir d'un seul nombre.

## Prévisions saisonnières (phase ultérieure)

Selon la documentation C3S, leur qualité dépend du lieu, de la variable, de l'échéance, des biais du modèle et des réanalyses historiques. Une valeur de prévision isolée ne suffit donc pas. Exiger métriques de qualité hors échantillon, hindcasts, dates et références ; abstention lorsque la qualité est insuffisante.

## Gestion des défaillances

- Pas de réécriture silencieuse : chaque changement d'octets NOAA crée une archive séparée.
- Échec de téléchargement/format : garder l'ancienne archive, ne pas remplacer par des données fictives.
- Sans fichier initial : montrer « aucune donnée chargée », jamais une valeur simulée présentée comme réelle.
- Les dates d'ingestion ne sont **pas** des dates de publication NOAA ; ne pas les confondre.

## Contrôle du format (11 octobre 2026)

Le fichier brut NOAA consultable à l'URL officielle présente bien l'en-tête `SEAS YR ANOM`, une série ordonnée commençant en DJF 1950 et, à la date du contrôle, une dernière ligne `JAS 2026 1.69` (+1,69 °C). Cette observation ne représente **pas** une probabilité de catastrophe. Référence : https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt

Nous avons vérifié le format et la documentation en ligne ; l'exécution complète du collecteur sur réseau doit être validée indépendamment. Le pipeline GitHub comprend un essai réseau non bloquant pour détecter les problèmes du fournisseur sans fragiliser les tests hors ligne.
